import streamlit as st
import folium
from streamlit_folium import st_folium
from datetime import datetime, timedelta
from database.process_hazard import get_recent_hazards
import matplotlib.pyplot as plt

def show_alert_map_ui():
    st.title("🌍 SafeIndy - Citywide Hazard Map")

    # Global CSS: full-column background coloring with borders
    st.markdown("""
        <style>
            div[data-testid="column"]:nth-of-type(1) {
                background-color: #fff9f0;
                padding: 1.5rem;
                border-radius: 12px;
                border: 2px solid #e0e0e0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            div[data-testid="column"]:nth-of-type(2) {
                background-color: #f0f7ff;
                padding: 1.5rem;
                border-radius: 12px;
                border: 2px solid #e0e0e0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .stButton > button {
                background-color: #ffcccc;
                color: black;
                font-weight: bold;
                border-radius: 6px;
                padding: 0.5rem 1rem;
                margin-top: 0.5rem;
                margin-bottom: 1rem;
            }
            .stMarkdown {
                margin-bottom: 1rem;
            }
        </style>
    """, unsafe_allow_html=True)

    left_col, right_col = st.columns([2, 1], gap="large")

    # ==== LEFT COLUMN ====
    with left_col:
        if st.button("⬅️ Return to ChatBot", key="return_btn"):
            st.session_state.show_map_mode = False
            st.experimental_set_query_params()

        st.subheader("🔎 Filter Alerts")

        fcol1, fcol2, fcol3 = st.columns(3)
        with fcol1:
            time_range = st.selectbox(
                "🕒 Time Range",
                ["Past 1 hour", "Past 2 hours", "Past 6 hours", "Past 24 hours"],
                key="map_time_range"
            )
        with fcol2:
            hazard_type = st.selectbox(
                "⚠️ Hazard Type",
                ["All", "Fire", "Crime", "Flood", "Accident", "Medical Emergency", "Other"],
                key="map_hazard_type"
            )
        with fcol3:
            severity = st.selectbox(
                "🔥 Severity",
                ["All", "Low", "Medium", "High", "Critical"],
                key="map_severity"
            )

        # Filtering logic
        time_mapping = {
            "Past 1 hour": timedelta(hours=1),
            "Past 2 hours": timedelta(hours=2),
            "Past 6 hours": timedelta(hours=6),
            "Past 24 hours": timedelta(hours=24)
        }

        hazards = get_recent_hazards(since=datetime.utcnow() - time_mapping[time_range])
        if hazard_type != "All":
            hazards = [h for h in hazards if h.get("hazard_type") == hazard_type]
        if severity != "All":
            hazards = [h for h in hazards if h.get("severity") == severity]

        # Folium map
        m = folium.Map(location=[39.7684, -86.1581], zoom_start=12)
        color_map = {
            "Low": "green",
            "Medium": "orange",
            "High": "red",
            "Critical": "darkred"
        }

        for h in hazards:
            popup_text = f"<b>{h.get('hazard_type')}</b> - {h.get('severity')}<br>{h.get('full_location')}"
            folium.Marker(
                location=[h["lat"], h["lon"]],
                popup=popup_text,
                icon=folium.Icon(color=color_map.get(h.get("severity"), "blue"))
            ).add_to(m)

        st_folium(m, height=500, width="100%")

    # ==== RIGHT COLUMN ====
    with right_col:
        st.subheader("📊 Hazard Type Distribution")

        type_counts = {}
        for h in hazards:
            h_type = h.get("hazard_type", "Other")
            type_counts[h_type] = type_counts.get(h_type, 0) + 1

        if type_counts:
            fig, ax = plt.subplots()
            ax.pie(type_counts.values(), labels=type_counts.keys(), autopct='%1.1f%%', startangle=90)
            ax.axis('equal')
            st.pyplot(fig)
        else:
            st.info("No hazards found for selected filters.")