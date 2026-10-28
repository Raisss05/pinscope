
import random
import re

import pandas as pd
import streamlit as st
import database as db

st.set_page_config(
    page_title="PinScope - Pinterest SEO",
    page_icon="📌",
    layout="wide",
)

# Sample data for our first dashboard.
# These scores are illustrative, NOT real Pinterest search volumes.

SAMPLE_DATA = [
    ("small bedroom ideas", "Home Decor", 82),
    ("small bedroom makeover", "Home Decor", 76),
    ("minimalist bedroom decor", "Home Decor", 71),
    ("cozy bedroom ideas", "Home Decor", 78),
    ("bedroom storage ideas", "Home Decor", 74),
    ("small balcony garden", "Gardening", 80),
    ("balcony plants for beginners", "Gardening", 73),
    ("vertical garden ideas", "Gardening", 75),
    ("indoor plants for beginners", "Gardening", 77),
    ("easy meal prep ideas", "Food", 85),
    ("healthy lunch ideas", "Food", 84),
    ("overnight oats recipes", "Food", 81),
    ("easy vegetarian dinner", "Food", 76),
    ("capsule wardrobe essentials", "Fashion", 79),
    ("casual outfit ideas", "Fashion", 77),
    ("minimalist summer outfits", "Fashion", 70),
    ("easy DIY home decor", "DIY", 80),
    ("DIY wall art ideas", "DIY", 72),
    ("budget room makeover", "DIY", 78),
    ("printable planner ideas", "Printables", 76),
]

def normalize(text):
    return re.sub(r"\s+", " ", str(text).strip().lower())

def relevance(keyword, query):
    keyword = normalize(keyword)
    query = normalize(query)

    if not query:
        return 50

    if keyword == query:
        return 100

    query_words = set(query.split())
    keyword_words = set(keyword.split())
    overlap = len(query_words & keyword_words)

    if query in keyword:
        return 90

    return int(20 + 75 * overlap / max(len(query_words), 1))

def create_title(keyword, style):
    phrase = keyword.strip().lower()
    phrase = phrase[0].upper() + phrase[1:]

    templates = {
        "List": [
            "10 " + phrase,
            phrase + ": 12 Ideas to Try",
            "The Ultimate Guide to " + phrase,
        ],
        "How-to": [
            "How to Create " + phrase,
            phrase + ": A Simple Step-by-Step Guide",
            "A Beginner's Guide to " + phrase,
        ],
        "Inspiration": [
            phrase + " for Your Next Project",
            "Beautiful " + phrase + " to Inspire You",
            "Save These " + phrase + " Ideas",
        ],
    }

    return random.choice(templates[style])


# Load our starter dataset.
df = pd.DataFrame(
    SAMPLE_DATA,
    columns=["keyword", "category", "sample_score"],
)

# Allow users to upload their own keyword CSV.
if "keyword_data" not in st.session_state:
    st.session_state.keyword_data = None

uploaded_file = st.sidebar.file_uploader(
    "Import keyword CSV",
    type=["csv"],
    help="CSV must include a keyword column.",
)

if uploaded_file is not None:
    try:
        imported_df = pd.read_csv(uploaded_file)
        imported_df.columns = [
            str(column).strip().lower()
            for column in imported_df.columns
        ]

        if "keyword" not in imported_df.columns:
            st.sidebar.error(
                "Your CSV needs a column named keyword."
            )
        else:
            if "category" not in imported_df.columns:
                imported_df["category"] = "Uncategorized"

            if "sample_score" not in imported_df.columns:
                imported_df["sample_score"] = None

            imported_df["keyword"] = (
                imported_df["keyword"]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.lower()
            )

            imported_df["category"] = (
                imported_df["category"]
                .fillna("Uncategorized")
                .astype(str)
            )

            imported_df["sample_score"] = pd.to_numeric(
                imported_df["sample_score"],
                errors="coerce",
            )

            imported_df = imported_df[
                imported_df["keyword"] != ""
            ]

            imported_df = imported_df.drop_duplicates(
                subset=["keyword"]
            )

            st.session_state.keyword_data = imported_df[
                ["keyword", "category", "sample_score"]
            ].reset_index(drop=True)

            db.save_keyword_dataset(st.session_state.keyword_data)

            st.sidebar.success(
                f"Loaded {len(imported_df)} keywords."
            )

    except Exception as error:
        st.sidebar.error(f"Could not read CSV: {error}")

# Load the keyword dataset from SQLite when no upload
# has been made during the current session.
if st.session_state.keyword_data is None:
    stored_data = db.load_keyword_dataset()

    if not stored_data.empty:
        st.session_state.keyword_data = stored_data

if st.session_state.keyword_data is not None:
    df = st.session_state.keyword_data.copy()


# Load saved keywords from the database.
if "saved_keywords" not in st.session_state:
    st.session_state.saved_keywords = db.load_saved_keywords()

# Sidebar navigation.
st.sidebar.title("📌 PinScope")
st.sidebar.caption("Pinterest SEO Research")
page = st.sidebar.radio(
    "Choose a page",
    [
        "Dashboard",
        "Keyword Explorer",
        "Pin SEO Assistant",
        "Saved Keywords",
    ],
)

st.sidebar.divider()
st.sidebar.caption("Starter version - sample data")

# DASHBOARD
if page == "Dashboard":
    st.title("📌 PinScope")
    st.subheader("Your Pinterest SEO dashboard")

    st.info(
        "This is a starter dataset. Sample scores are for demonstration "
        "only and are not official Pinterest metrics."
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Keywords", len(df))
    col2.metric("Categories", df["category"].nunique())
    col3.metric(
        "Saved keywords",
        len(st.session_state.saved_keywords),
    )

    st.subheader("Keywords by category")
    st.bar_chart(df["category"].value_counts())

    st.subheader("Example keywords")
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "Download keyword dataset",
        df.to_csv(index=False).encode("utf-8"),
        file_name="pinscope_keywords.csv",
        mime="text/csv",
    )

# KEYWORD EXPLORER
elif page == "Keyword Explorer":
    st.title("🔎 Keyword Explorer")
    st.write("Search the starter dataset for relevant keyword ideas.")

    query = st.text_input(
        "Enter a keyword",
        placeholder="Try small bedroom ideas",
    )

    categories = ["All"] + sorted(df["category"].unique().tolist())
    category = st.selectbox("Category", categories)

    minimum = st.slider("Minimum relevance score", 0, 100, 0)

    results = df.copy()
    results["relevance"] = results["keyword"].apply(
        lambda word: relevance(word, query)
    )

    if query.strip():
        q = normalize(query)
        results = results[
            results["keyword"].str.contains(
                re.escape(q), na=False
            )
            | (results["relevance"] >= 50)
        ]

    if category != "All":
        results = results[results["category"] == category]

    results = results[results["relevance"] >= minimum]
    results = results.sort_values(
        "relevance", ascending=False
    )

    st.write(f"Matching keywords: {len(results)}")

    st.dataframe(
        results,
        use_container_width=True,
        hide_index=True,
    )

    choices = results["keyword"].tolist()
    selected = st.multiselect(
        "Choose keywords to save",
        choices,
    )

    if st.button("Save selected keywords"):
    db.save_keywords(selected)
    st.session_state.saved_keywords = db.load_saved_keywords()
    st.success("Your selected keywords have been saved.")

    st.download_button(
        "Export search results",
        results.to_csv(index=False).encode("utf-8"),
        file_name="pinscope_search.csv",
        mime="text/csv",
    )

# PIN SEO ASSISTANT
elif page == "Pin SEO Assistant":
    st.title("✨ Pin SEO Assistant")
    st.write("Create draft Pinterest titles from a keyword.")

    keyword = st.text_input(
        "Main keyword",
        placeholder="Try small balcony garden",
    )

    style = st.selectbox(
        "Choose a title style",
        ["List", "How-to", "Inspiration"],
    )

    if st.button("Generate title ideas", type="primary"):
        if not keyword.strip():
            st.warning("Please enter a keyword first.")
        else:
            st.subheader("Suggested Pin titles")

            for i in range(3):
                st.write(f"{i + 1}. {create_title(keyword, style)}")

            st.subheader("Description draft")
            st.write(
                f"Discover {keyword} with practical tips and "
                "inspiration. Save these ideas for your next project "
                "and explore more ideas to suit your style."
            )

            st.caption(
                "Review these drafts before publishing. They are "
                "template-generated, not AI-generated."
            )

# SAVED KEYWORDS
elif page == "Saved Keywords":
    st.title("⭐ Saved Keywords")

    saved = st.session_state.saved_keywords

    if not saved:
        st.info(
            "No saved keywords yet. Visit Keyword Explorer to add some."
        )
    else:
        saved_df = pd.DataFrame({"keyword": saved})

        st.dataframe(
            saved_df,
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "Download saved keywords",
            saved_df.to_csv(index=False).encode("utf-8"),
            file_name="pinscope_saved_keywords.csv",
            mime="text/csv",
        )

        
        if st.button("Clear saved keywords"):
    db.clear_saved_keywords()
    st.session_state.saved_keywords = []
    st.rerun()

st.divider()
st.caption(
    "PinScope - independent Pinterest research prototype. "
    "No live Pinterest data is connected."
)
