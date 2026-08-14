from openai import OpenAI
import numpy as np
from sklearn.decomposition import PCA
import plotly.graph_objects as go
from dotenv import load_dotenv
import os

# Load API key from .env file
load_dotenv()
api_key = os.getenv('NRP_API_KEY')
# Ensure the API key is available
if not api_key:
    raise ValueError("No NRP_API_KEY found. Please check your .env file.")
client = OpenAI(
    base_url=os.getenv("NRP_BASE_URL"),
    api_key=api_key,
)

def get_embedding(text, model="qwen3-embedding"):
    text = text.replace("\n", " ")
    return client.embeddings.create(input = [text], model=model).data[0].embedding

# Sample documents
documents = [
    "The sky is blue and beautiful.",
    "Love this blue and beautiful sky!",
    "The quick brown fox jumps over the lazy dog.",
    "A king's breakfast has sausages, ham, bacon, eggs, toast, and beans",
    "I love green eggs, ham, sausages and bacon!",
    "The brown fox is quick and the blue dog is lazy!",
    "The sky is very blue and the sky is very beautiful today",
    "The dog is lazy but the brown fox is quick!"
]

# Generate embeddings for each document
embeddings = [get_embedding(doc) for doc in documents]

# Convert embeddings to a numpy array for PCA
embeddings_array = np.array(embeddings)

print(embeddings_array.shape)

# Applying PCA to reduce dimensions to 3
pca = PCA(n_components=3)
reduced_embeddings = pca.fit_transform(embeddings_array)

# Creating a 3D plot using Plotly
fig = go.Figure(data=[go.Scatter3d(
    x=reduced_embeddings[:,0],
    y=reduced_embeddings[:,1],
    z=reduced_embeddings[:,2],
    mode='markers+text',
    text=documents,  # Adding document texts for hover
    hoverinfo='text',  # Showing only the text on hover
    marker=dict(
        size=12,
        color=list(range(len(documents))),  # Assigning a unique color to each document
        opacity=0.8
    )
)])

# Adding titles and labels to the plot
fig.update_layout(title="3D Plot of Document Embeddings",
                  scene=dict(
                      xaxis_title='PCA Component 1',
                      yaxis_title='PCA Component 2',
                      zaxis_title='PCA Component 3'
                  ))

fig.show()