import kagglehub

# Download latest version
path = kagglehub.dataset_download("asjad99/mimiciii")

print("Path to dataset files:", path)