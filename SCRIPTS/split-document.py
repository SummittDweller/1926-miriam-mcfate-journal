import os

import re

def slugify(filename):
    filename = filename.lower().strip()
    filename = re.sub(r'[^a-z0-9\s_-]', '', filename)
    filename = re.sub(r'[\s_-]+', '-', filename)
    filename = re.sub(r'^-+|-+$', '', filename)
    return filename


def split_document(input_file, output_dir="output_documents"):
    """Splits a text document into smaller documents based on ## subheadings.

    Args:  THESE ARE HARD CODED NOW!
        input_file (str): Path to the input text file.
        output_dir (str, optional): Directory to store the output documents. 
                                    Defaults to "output_documents".
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    current_doc_lines = []
    doc_count = 0
    filenames = []

    for line in lines:
        if line.startswith("## "):  # Assumes subheadings are marked with ##
            
            if current_doc_lines:
                output_file = os.path.join(output_dir, f"file_{doc_count:03}.txt")
                with open(output_file, 'w', encoding='utf-8') as outfile:
                    outfile.writelines(current_doc_lines)
                doc_count += 1
                current_doc_lines = []
            
            # New subheading/file encountered... begin with three lines of frontmatter
            current_doc_lines.append('---  \n')
            current_doc_lines.append('title: "' + line[2:].strip( ) + '"  \n')
            current_doc_lines.append('---  \n')

            current_doc_lines.append(line)  # Add the subheading line to the new doc
            heading = line[2:].strip( )
            filenames.append(f"{doc_count:03}-{slugify(heading)}.md")
            
        else:
            current_doc_lines.append(line)
    

    # Save the last document
    if current_doc_lines:
        output_file = os.path.join(output_dir, f"file_{doc_count:03}.txt")
        with open(output_file, 'w', encoding='utf-8') as outfile:
            outfile.writelines(current_doc_lines)

    # Rename the temporary files
    count = 0
    for fname in filenames:
        temp = os.path.join(output_dir, f"file_{count:03}.txt")
        os.rename(temp, os.path.join(output_dir, fname))
        count += 1
        

if __name__ == "__main__":
    input_file_path = "objects/markdown/McFate-Travel-Diary.md"
    output_file_path = "objects/markdown/"
    split_document(input_file_path, output_file_path)