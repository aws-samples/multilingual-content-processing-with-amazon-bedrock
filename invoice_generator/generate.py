from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

import json
import os

# Load data for the invoice
with open('./data/japanese_invoice_data.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# Load templates
env = Environment(
    loader=FileSystemLoader(searchpath='./templates'),
    autoescape=False  # nosec B701: We are not autoescaping intentionally in this use case since this is used internally to generate synthetic documents
) 

template = env.get_template('template.html')

# Render the template with data
output = template.render(data)
print(output)

tmp_html_file = 'tmp_invoice.html'
with open(tmp_html_file, 'w', encoding='utf-8') as file:
    file.write(output)

HTML(tmp_html_file).write_pdf('output_invoice.pdf')

os.remove(tmp_html_file)