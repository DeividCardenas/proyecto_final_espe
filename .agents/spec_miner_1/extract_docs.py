import zipfile
import xml.etree.ElementTree as ET
import os
import sys

def extract_docx_text(docx_path):
    print(f"=== Extracting from: {docx_path} ===")
    if not os.path.exists(docx_path):
        print(f"File not found: {docx_path}")
        return ""
    
    with zipfile.ZipFile(docx_path) as z:
        # Check files in zip
        namelist = z.namelist()
        xml_content = z.read('word/document.xml')
        
    tree = ET.fromstring(xml_content)
    namespaces = {
        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    }
    
    body = tree.find('w:body', namespaces)
    if body is None:
        return "No body found in document"
    
    extracted_lines = []
    
    for child in body:
        tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
        if tag == 'p': # paragraph
            texts = [node.text for node in child.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t') if node.text]
            p_text = "".join(texts).strip()
            if p_text:
                extracted_lines.append(f"[P] {p_text}")
        elif tag == 'tbl': # table
            extracted_lines.append("\n--- TABLE START ---")
            rows = child.findall('w:tr', namespaces)
            for r_idx, row in enumerate(rows):
                cells = row.findall('w:tc', namespaces)
                cell_texts = []
                for cell in cells:
                    c_p_texts = []
                    for cp in cell.findall('w:p', namespaces):
                        t_parts = [node.text for node in cp.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t') if node.text]
                        if t_parts:
                            c_p_texts.append("".join(t_parts))
                    cell_texts.append(" | ".join(c_p_texts).strip())
                extracted_lines.append(f"Row {r_idx}: " + " /// ".join(cell_texts))
            extracted_lines.append("--- TABLE END ---\n")
            
    return "\n".join(extracted_lines)

if __name__ == '__main__':
    doc1 = r"c:\Users\Lab Creacion Digital\Documents\proyecto espe\FichaDeProyecto_EspBigData_Completada.docx"
    doc2 = r"c:\Users\Lab Creacion Digital\Documents\proyecto espe\FichaDeProyecto_EspBigData (2).docx"
    
    out1 = extract_docx_text(doc1)
    with open(r"c:\Users\Lab Creacion Digital\Documents\proyecto espe\.agents\spec_miner_1\doc1_extracted.txt", "w", encoding="utf-8") as f:
        f.write(out1)
        
    out2 = extract_docx_text(doc2)
    with open(r"c:\Users\Lab Creacion Digital\Documents\proyecto espe\.agents\spec_miner_1\doc2_extracted.txt", "w", encoding="utf-8") as f:
        f.write(out2)
        
    print("Done! Files written to doc1_extracted.txt and doc2_extracted.txt")
