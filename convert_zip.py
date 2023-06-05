import os
import zipfile

def zip_folder(folder_path, output_path):
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, folder_path))



def convert_to_zip(userid,folder_name):
    current_path = os.getcwd()
    output_file_name = f'{folder_name}.zip'
    inputp = f'/saved_data/{userid}/{folder_name}'
    outputp =f'/saved_data/{userid}/{output_file_name}'
    joined_input_path = current_path + inputp
    joined_output_path = current_path + outputp
    zip_folder(joined_input_path,joined_output_path)
    

__all__ = ['convert_to_zip']