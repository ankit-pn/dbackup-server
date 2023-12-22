import os
import zipfile

def extract_zip_files(folder_path):
    for subfolder in os.listdir(folder_path):
        subfolder_path = os.path.join(folder_path, subfolder, 'Takeout')
        if os.path.exists(subfolder_path):
            for filename in os.listdir(subfolder_path):
                if filename.startswith('takeout-') and filename.endswith('.zip'):
                    zip_path = os.path.join(subfolder_path, filename)
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        # Check if any file in the zip already exists in the destination folder
                        should_extract = True
                        for file_info in zip_ref.infolist():
                            if os.path.exists(os.path.join(subfolder_path, file_info.filename)):
                                should_extract = False
                                print(f"Skipping extraction of {filename} in {subfolder_path} as it seems to be already extracted.")
                                break
                        if should_extract:
                            zip_ref.extractall(subfolder_path)
                            print(f"Extracted {filename} in {subfolder_path}")

def extract_all():
    folder_path = 'saved_data'  # Replace with the actual path if needed
    extract_zip_files(folder_path)

__all__ = ['extract_all']
