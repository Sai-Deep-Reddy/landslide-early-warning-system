import os
import sys
import win32com.client

PPTX_PATH = os.path.abspath(r"C:\Users\saide\Downloads\SIH2026_PS26001_LEWS_Presentation.pptx")
PDF_PATH = os.path.abspath(r"C:\Users\saide\Downloads\SIH2026_PS26001_LEWS_Presentation.pdf")
EXPORT_IMG_DIR = os.path.abspath(os.path.join(os.getcwd(), "slide_assets", "exported_slides"))
os.makedirs(EXPORT_IMG_DIR, exist_ok=True)

print("Opening PowerPoint via COM...")
ppt_app = win32com.client.Dispatch("PowerPoint.Application")

try:
    pres = ppt_app.Presentations.Open(PPTX_PATH, WithWindow=False)
    print(f"Loaded presentation: {PPTX_PATH}")
    print(f"Slide count: {pres.Slides.Count}")
    
    # 1. Export to PDF (FormatType: 32 = ppSaveAsPDF)
    print(f"Exporting to PDF: {PDF_PATH}")
    pres.SaveAs(PDF_PATH, 32)
    print("PDF export successful!")
    
    # 2. Export each slide as PNG image
    for idx, slide in enumerate(pres.Slides, 1):
        img_file = os.path.join(EXPORT_IMG_DIR, f"slide_{idx}.png")
        # Export(FileName, FilterName, ScaleWidth, ScaleHeight)
        slide.Export(img_file, "PNG", 1920, 1080)
        print(f"Exported slide {idx} image: {img_file}")
        
    pres.Close()
except Exception as e:
    print("Error during export:", e)
finally:
    ppt_app.Quit()

print("All export operations completed successfully!")
