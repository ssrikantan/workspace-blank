"""
Azure Video Retrieval App
This Streamlit application allows users to search for video frames based on visual or speech cues using Azure Video Indexer and Azure Blob Storage.
Modules:
    - streamlit: For creating the web application interface.
    - requests: For making HTTP requests to the Azure Video Indexer API.
    - dotenv: For loading environment variables from a .env file.
    - os: For accessing environment variables.
    - pandas: For handling data in DataFrame format.
    - azure.storage.blob: For generating SAS tokens for accessing Azure Blob Storage.
    - datetime: For handling date and time operations.
Functions:
    - search_videos(query, query_type): Searches for video frames based on the user's query and query type (Vision or Speech).
    - get_video_url(document_id, best_time): Retrieves the SAS URL for the video document based on the document ID and best timestamp.
    - reset_search(): Resets the search results and selected video when the search type changes.
Streamlit App:
    - Displays a title and sidebar for user input.
    - Allows users to search for video frames by entering a query and selecting a search type (Vision or Speech).
    - Displays search results in a table with checkboxes for selecting videos to play.
    - Plays the selected video in the main layout with the best timestamp.
Environment Variables:
    - az-video-indexer-endpoint: Azure Video Indexer endpoint.
    - az-video-indexer-index-name: Azure Video Indexer index name.
    - az-video-indexer-api-version: Azure Video Indexer API version.
    - az-video-indexer-key: Azure Video Indexer subscription key.
    - az-storage-account-name: Azure Storage account name.
    - az-storage-container-name: Azure Storage container name.
    - az-storage-account-key: Azure Storage account key.
"""

import requests
import streamlit as st
from dotenv import load_dotenv
import os
import pandas as pd

load_dotenv()

from azure.storage.blob import (
    generate_container_sas,
    ContainerSasPermissions,
)
import datetime

# Set the page to open in wide mode
st.set_page_config(layout="wide")

# Replace with your Azure Video Indexer credentials
az_video_indexer_endpoint = os.getenv("az-video-indexer-endpoint")
az_video_indexer_index_name = os.getenv("az-video-indexer-index-name")
az_video_indexer_api_version = os.getenv("az-video-indexer-api-version")
az_video_indexer_key = os.getenv("az-video-indexer-key")

az_storage_account_name = os.getenv("az-storage-account-name")
az_storage_container_name = os.getenv("az-storage-container-name")
az_storage_account_key = os.getenv("az-storage-account-key")

# Query templates for searching by text or speech
query_by_text = {
    "queryText": "<user query>",
    "filters": {
        "featureFilters": ["vision"],
    },
}

query_by_speech = {
    "queryText": "<user query>",
    "filters": {
        "featureFilters": ["speech"],
    },
}


# Function to search for video frames based on user input, from the Azure Video Retrieval Service
def search_videos(query, query_type):
    url = f"https://{az_video_indexer_endpoint}/computervision/retrieval/indexes/{az_video_indexer_index_name}:queryByText?api-version={az_video_indexer_api_version}"
    headers = {
        "Ocp-Apim-Subscription-Key": az_video_indexer_key,
        "Content-Type": "application/json",
    }

    input_query = None
    if query_type == "Speech":
        query_by_speech["queryText"] = query
        input_query = query_by_speech
    else:
        query_by_text["queryText"] = query
        input_query = query_by_text
    try:
        response = requests.post(url, headers=headers, json=input_query)
        response.raise_for_status()
        print("search response \n", response.json())
        return response.json()
    except Exception as e:
        print("error", e.args)
        print("error", e)
        return None


# Function to retrieve the SAS URL for the video document based on the document ID and best timestamp
def get_video_url(document_id, best_time):
    url = f"https://{az_video_indexer_endpoint}/computervision/retrieval/indexes/{az_video_indexer_index_name}/documents?api-version={az_video_indexer_api_version}"
    headers = {
        "Ocp-Apim-Subscription-Key": az_video_indexer_key,
        "Content-Type": "application/json",
    }
    response = requests.get(url, headers=headers)
    sas_token = None
    for document in response.json().get("value"):
        if document.get("documentId") == document_id:
            try:
                sas_token = generate_container_sas(
                    account_name=az_storage_account_name,
                    account_key=az_storage_account_key,
                    container_name=az_storage_container_name,
                    permission=ContainerSasPermissions(read=True, list=True),
                    expiry=datetime.datetime.utcnow()
                    + datetime.timedelta(hours=1),  # Token valid for 1 hour
                )
            except Exception as e:
                print(f"Error generating SAS URL: {e}")
                return None
            sas_url = (
                document.get("documentUrl") + "?start=" + best_time + "&" + sas_token
            )
            print("video sas url retrieved \n", sas_url)
            return sas_url


# Streamlit App
st.title("Multi Modal Video Search")
st.sidebar.header("Search for Frames")


# Add a callback to reset search results and selected video when search type changes
def reset_search():
    st.session_state.search_results = None
    st.session_state.selected_video = None


search_type = st.sidebar.radio(
    "Search by:", ["Vision", "Speech"], key="search_type_radio", on_change=reset_search
)

# Input for search query
query = st.sidebar.text_input(
    "Enter your search query (e.g., visual cue, spoken words):"
)

if "search_results" not in st.session_state:
    st.session_state.search_results = None
# Initialize session state for selected video
if "selected_video" not in st.session_state:
    st.session_state.selected_video = None

if st.sidebar.button("Search"):
    with st.spinner("Fetching search results..."):

        # Step 2: Perform search
        results = search_videos(query, query_type=search_type)
        if results and "value" in results:
            st.session_state.search_results = pd.DataFrame(
                results["value"]
            ).sort_values(by="relevance", ascending=False)
        else:
            st.session_state.search_results = None
            st.write("No results found.")

# Main layout
col1, col2 = st.columns([1, 2])  # Adjust column ratios as needed

# Left column: Search results
with col1:
    st.subheader("Search Results")
    selected_video_index = None
    if st.session_state.search_results is not None:
        results_df = st.session_state.search_results

        # Add a checkbox column to the DataFrame
        results_df["Select"] = False  # Placeholder for selection state
        with st.form("video_selection_form"):
            # Play button at the top
            selected_indexes = st.multiselect(
                "Select videos to play",
                results_df.index,
                format_func=lambda x: f"{results_df.iloc[x]['documentId']} (Best: {results_df.iloc[x]['best']})",
            )

            if st.form_submit_button("Play") and selected_indexes:
                # Pick the first selected video
                selected_video_index = selected_indexes[0]
                row = results_df.iloc[selected_video_index]
                st.session_state.selected_video = {
                    "document_id": row["documentId"],
                    "best_time": row["best"],
                    "start_time": row["start"],
                    "end_time": row["end"],
                    "document_kind": row["documentKind"],
                }
                # Display the table with checkboxes


# Right column: Video player
with col2:
    if st.session_state.selected_video:
        selected_video = st.session_state.selected_video
        st.subheader(f"Playing Video: {selected_video['document_id']}")
        st.write(f"Best Timestamp: {selected_video['best_time']}")
        st.write(
            f"Start: {selected_video['start_time']}, End: {selected_video['end_time']}"
        )

        # Get the video URL
        video_url = get_video_url(
            selected_video["document_id"], selected_video["best_time"]
        )

        # best_time  value is in the format  '00:00:11.0110000'
        # Convert the best time to seconds
        best_time_parts = selected_video["best_time"].split(":")
        best_time_seconds = (
            int(best_time_parts[0]) * 3600
            + int(best_time_parts[1]) * 60
            + float(best_time_parts[2])
        )

        st.video(video_url, start_time=int(best_time_seconds), autoplay=True)
    # else:
    #     st.write("Select a video from the search results to play it here.")

if st.session_state.search_results is not None:
    results_df = st.session_state.search_results
    st.dataframe(
        results_df[["documentId", "best", "start", "end", "documentKind"]],
        use_container_width=True,
    )  # Auto width to fit the page
