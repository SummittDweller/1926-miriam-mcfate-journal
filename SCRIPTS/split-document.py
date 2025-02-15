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

    doc_count = 0
    frontmatter = 0
    outfile = False

    for line in lines:
        
        if line.startswith('---'):
            frontmatter += 1
            continue;        # found a frontmatter marker, continue to next line
        if frontmatter < 2:
            continue         # not yet past the frontmatter so continue to next line

        if line.startswith("## "):  # Assumes subheadings are marked with ##... make a new file

            # If we have an open outfile, close it
            if outfile:
                outfile.close( )

            # Open a new .md outfile
            heading = line[2:].strip( )
            filename = f"{doc_count:03}-{slugify(heading)}.md"
            output_file = os.path.join(output_dir, filename)
            outfile = open(output_file, 'w', encoding='utf-8')
            doc_count += 1
            
            # New subheading/file encountered... begin with three lines of frontmatter
            outfile.write('---  \n')
            outfile.write('title: "' + line[2:].strip( ) + '"  \n')
            outfile.write('---  \n')
        
        if outfile:
            outfile.write(line)
    
    # Save the last document
    if outfile:
        outfile.close( )
        

if __name__ == "__main__":
    input_file_path = "objects/markdown/McFate-Travel-Diary.md"
    output_file_path = "objects/markdown/"
    split_document(input_file_path, output_file_path)