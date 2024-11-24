# Multimodal video search

This sample Application showcases how one could perform multi modal search across videos in a catalog. Users could search based on visual cues in the video, or based on speech in the video. There is no pre-requisite for transcriptions to be available in the video

## Services used

Azure Video Retrieval Service is used to index the Videos for search. The Videos are ingested based on their URL (location) inside an Azure Blob Storage Container. These could reside anywhere else too as long as they can be accessed through a url.
Once ingested, the Video Retrieval Service allows for search based on visual or speech cues from the user

### Using the Sample Application

The user could select whether they would like to search based on visual or speech cues, and provide their input.
The Video Retrieval Service returns the videos that contain matching frames along with the timestamp when they occur during the video
