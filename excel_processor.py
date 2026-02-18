import pandas as pd
import logging
from pathlib import Path

def process_excel_to_markdown(excel_path: str, output_markdown_path: str):
    """
    Processes all sheets in an Excel file into a compressed Markdown grid.
    
    Args:
        excel_path (str): Path to the .xlsx or .xls file.
        output_markdown_path (str): Path where the resulting .md should be saved.
    """
    logging.info(f"🚀 Starting Excel processing for: {excel_path}")
    
    try:
        # Read all sheets (sheet_name=None returns a dict)
        sheets_dict = pd.read_excel(excel_path, sheet_name=None)
        
        full_markdown = []
        
        for sheet_name, df in sheets_dict.items():
            # Skip empty sheets
            if df.empty:
                logging.warning(f"Skipping empty sheet: {sheet_name}")
                continue
                
            logging.info(f"📄 Processing sheet: {sheet_name} ({len(df)} rows found)")
            
            # --- The Cleanup Ritual ---
            
            # 1. Strip edge emptiness (Rows & Columns)
            df = df.dropna(how='all', axis=0).dropna(how='all', axis=1)
            
            # 2. Handle Merged Cells (Basic version)
            # Forward fill allows orphaned data to find its parent header
            # We only ffill if it makes sense (usually horizontal headers)
            df = df.ffill(axis=1) 
            
            # 3. Clean NaN/Nulls for the LLM
            df = df.fillna("")
            
            # 4. Generate the Compressed Grid
            # Prepend Sheet name so Gemini knows the specific context
            sheet_content = f"### EXTERNAL DATA SOURCE: Excel Sheet - {sheet_name}\n\n"
            
            if not df.empty:
                sheet_content += df.to_markdown(index=False)
            else:
                sheet_content += "*[Sheet was found but contained no structured data]*"
                
            full_markdown.append(sheet_content)
            
        # Join all sheets with a separator
        final_content = "\n\n" + "\n\n---\n\n".join(full_markdown) + "\n\n"
        
        # Save to the same location the pipeline expects markdown
        with open(output_markdown_path, 'w') as f:
            f.write(final_content)
            
        logging.info(f"✅ Excel conversion successful. Markdown saved to: {output_markdown_path}")
        return True

    except Exception as e:
        logging.error(f"❌ Failed to process Excel file: {e}")
        raise e
