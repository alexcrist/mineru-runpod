import modal

func = modal.Function.from_name("mineru", "process_pdf")

result = func.remote("2021_International_Residential_Code_Chapter_3_Page_8_Images.pdf")

print("result", result)
