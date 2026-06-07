import streamlit as st
st.set_page_config(page_title="Treasures", page_icon="💎", layout="wide")

st.title("💎 Treasures — Daily Free Stuff Finder")
st.write("✅ If you see this, your app is finally working!")

st.markdown("## 🌐 Source Sites")
st.markdown("- Contest Reminder")
st.markdown("- Contest Bee")
st.markdown("- Freebie Shark")
st.markdown("- Freebie Guy")
st.markdown("- Daily Free Stuff")
st.markdown("- TrySpree")

st.divider()

search = st.text_input("Search")

items = ["Gift Card", "iPhone", "Free Samples"]

for item in items:
    st.write(item)

st.caption("App is live ✅")
