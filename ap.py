import streamlit as st
import pandas as pd
import itertools

# Provided Topics and Descriptions
topics_data = [
    {"Topic": "Python Data Types and Variables", "Description": "Lists, Tuples, Sets, Dictionaries"},
    {"Topic": "Control Flow in Python", "Description": "Conditional statements (if-else), loops (for, while)"},
    {"Topic": "Functions in Python", "Description": "Defining and calling functions, arguments, return values"},
    {"Topic": "File Handling in Python", "Description": "Reading and writing files (open(), read(), write())"},
    {"Topic": "Exception Handling", "Description": "try, except, finally"},
    {"Topic": "Higher-Order Functions", "Description": "map(), filter(), reduce()"},
    {"Topic": "Object-Oriented Programming (OOP)", "Description": "OOP concepts"}
]

@st.cache_data
def load_data(file_path):
    try:
        df = pd.read_csv(file_path).apply(lambda x: x.str.strip() if x.dtype == 'object' else x)
        if not {'name', 'marks'}.issubset(df.columns.str.lower()):
            st.error("CSV must contain 'Name' and 'Marks' columns.")
            return None
        df.columns = df.columns.str.lower()
        return df[['name', 'marks']].astype({'marks': 'int'})
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None


def categorize_students(data):
    bins = [-1, 25, 35, 100]
    labels = ['<25', '25-35', '>35']
    data['category'] = pd.cut(data['marks'], bins=bins, labels=labels)
    return data


def create_balanced_batches(data):
    categorized = {label: data[data['category'] == label] for label in ['>35', '25-35', '<25']}
    batches = []

    while any(len(v) > 0 for v in categorized.values()):
        batch = pd.concat([categorized[label].iloc[:2] for label in ['>35', '25-35']] + [categorized['<25'].iloc[:1]],
                          ignore_index=True)
        for label in categorized:
            categorized[label] = categorized[label].iloc[len(batch[batch['category'] == label]):]

        if not batch.empty:
            batches.append(batch)

    return batches


def assign_topics(batches, topics, weeks=5):
    topic_cycle = itertools.cycle(topics)
    assignments = []

    for week in range(1, weeks + 1):
        for i, batch in enumerate(batches):
            topic = next(topic_cycle)
            assignments.append({"Week": week, "Batch": f"Batch {i + 1}", "Topic": topic["Topic"]})

    return assignments


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


st.title("Efficient Student Clustering & Topic Assignment")
uploaded_file = st.file_uploader("Upload CSV (Name, Marks)", type=["csv"])

if uploaded_file:
    data = load_data(uploaded_file)
    if data is not None:
        data = categorize_students(data)
        batches = create_balanced_batches(data)
        topic_assignments = assign_topics(batches, topics_data, weeks=5)
        output = prepare_output(batches, topic_assignments)

        st.write("### Structured Output: Name, Batch, Weekly Topics")
        st.dataframe(output)

        st.download_button(
            label="Download Output CSV",
            data=output.to_csv(index=False).encode('utf-8'),
            file_name="student_batch_topics.csv",
            mime='text/csv'
        )