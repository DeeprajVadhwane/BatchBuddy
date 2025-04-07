import streamlit as st
import pandas as pd
import itertools
import zipfile
import io

st.set_page_config(page_title="Student Clustering and Topic Assignment", layout="wide")

# --- Dynamic Topic Input ---
st.sidebar.header("📘 Add Weekly Topics")
default_topics = [
    {"Topic": "Python Data Types and Variables", "Description": "Lists, Tuples, Sets, Dictionaries"},
    {"Topic": "Control Flow in Python", "Description": "Conditional statements (if-else), loops (for, while)"},
    {"Topic": "Functions in Python", "Description": "Defining and calling functions, arguments, return values"},
    {"Topic": "File Handling in Python", "Description": "Reading and writing files (open(), read(), write())"},
    {"Topic": "Exception Handling", "Description": "try, except, finally"},
    {"Topic": "Higher-Order Functions", "Description": "map(), filter(), reduce()"},
    {"Topic": "Object-Oriented Programming (OOP)", "Description": "OOP concepts"}
]

custom_topics = []
num_topics = st.sidebar.number_input("How many topics do you want to enter?", min_value=0, value=0)

for i in range(num_topics):
    topic = st.sidebar.text_input(f"Topic {i+1} Title", key=f"topic_{i}")
    desc = st.sidebar.text_input(f"Description for Topic {i+1}", key=f"desc_{i}")
    if topic:
        custom_topics.append({"Topic": topic, "Description": desc})

# Check if topics are missing, and ask for default usage
if num_topics == 0 or len(custom_topics) == 0:
    st.sidebar.warning("⚠️ No custom topics provided.")
    use_default = st.sidebar.checkbox("✅ Use default weekly topics?", value=True)
    if use_default:
        custom_topics = default_topics.copy()

# --- Load and Clean Multiple Files ---
@st.cache_data
def load_and_clean_data(uploaded_files):
    all_data = []
    for file in uploaded_files:
        try:
            df = pd.read_csv(file)
            df.columns = df.columns.str.lower().str.strip()
            if 'name' not in df.columns or 'score' not in df.columns:
                st.error(f"{file.name} must contain 'Name' and 'Score' columns.")
                continue
            df = df[['name', 'score']].dropna()
            df['score'] = df['score'].apply(lambda x: eval(x.split('/')[0].strip()) / eval(x.split('/')[1].strip()) * 100)
            all_data.append(df)
        except Exception as e:
            st.error(f"Error in file {file.name}: {e}")
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return pd.DataFrame()

# --- Categorize by Percentage ---
def categorize_students(data):
    bins = [-1, 40, 70, 100]
    labels = ['Low', 'Medium', 'High']
    data['category'] = pd.cut(data['score'], bins=bins, labels=labels)
    return data

# --- Create Balanced Batches ---
def create_balanced_batches(data):
    categorized = {label: data[data['category'] == label] for label in ['High', 'Medium', 'Low']}
    batches = []

    while any(len(v) > 0 for v in categorized.values()):
        batch = pd.concat([categorized[label].iloc[:2] for label in ['High', 'Medium']] + [categorized['Low'].iloc[:1]],
                          ignore_index=True)
        for label in categorized:
            categorized[label] = categorized[label].iloc[len(batch[batch['category'] == label]):]
        if not batch.empty:
            batches.append(batch)

    return batches

# --- Assign Topics to Batches Week-wise ---
def assign_topics(batches, topics, weeks=5):
    topic_cycle = itertools.cycle(topics)
    assignments = []
    for week in range(1, weeks + 1):
        for i, batch in enumerate(batches):
            topic = next(topic_cycle)
            assignments.append({"Week": week, "Batch": f"Batch {i + 1}", "Topic": topic["Topic"]})
    return assignments

# --- Prepare Final Output ---
def prepare_output(batches, assignments):
    result = pd.concat(
        [pd.DataFrame({'Name': batch['name'], 'Batch': f"Batch {i + 1}"}) for i, batch in enumerate(batches)],
        ignore_index=True
    )

    assignment_df = pd.DataFrame(assignments)
    for week in range(1, assignment_df['Week'].max() + 1):
        week_topics = assignment_df[assignment_df['Week'] == week].set_index('Batch')['Topic']
        result[f"Week {week} Topic"] = result['Batch'].map(week_topics)

    return result

# --- Export Batch Plans Individually ---
def export_batches_individually(batches):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        for i, batch in enumerate(batches):
            batch_name = f"Batch_{i + 1}.csv"
            batch_df = batch[['name', 'score', 'category']]
            csv_data = batch_df.to_csv(index=False)
            zipf.writestr(batch_name, csv_data)
    zip_buffer.seek(0)
    return zip_buffer

# --- Main UI ---
st.title("🎯 Efficient Student Clustering & Weekly Topic Assignment")

uploaded_files = st.file_uploader("📂 Upload one or more CSV files (with 'Name' and 'Score' columns)", type="csv", accept_multiple_files=True)

if uploaded_files:
    data = load_and_clean_data(uploaded_files)
    if not data.empty:
        st.success(f"✅ Total Students Processed: {len(data)}")
        data = categorize_students(data)
        batches = create_balanced_batches(data)
        topic_assignments = assign_topics(batches, custom_topics, weeks=5)
        output = prepare_output(batches, topic_assignments)

        st.write("### 📋 Final Output: Batch and Topic Assignment")
        st.dataframe(output)

        st.download_button(
            label="📥 Download All Assignments (CSV)",
            data=output.to_csv(index=False).encode('utf-8'),
            file_name="student_batch_topics.csv",
            mime='text/csv'
        )

        zip_buffer = export_batches_individually(batches)
        st.download_button(
            label="📦 Download Individual Batch Plans (ZIP)",
            data=zip_buffer,
            file_name="batches.zip",
            mime="application/zip"
        )
