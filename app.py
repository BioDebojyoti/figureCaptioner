import base64
import io
from dash import Dash, html, dcc, Input, Output, State, ctx, ALL
import dash_bootstrap_components as dbc
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter
from pdf2image import convert_from_bytes
from io import BytesIO

# Use Bootstrap theme
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])

# In-memory storage
pdf_storage = {}

# Layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H2("PDF Figure Caption Tool", className="text-center text-info mb-4"), width=12)
    ]),

    dbc.Tabs([
        dbc.Tab(label="Upload & Captions", tab_id="upload", children=[
            dbc.Card([
                dbc.CardBody([
                    dcc.Upload(
                        id='upload-pdf',
                        children=dbc.Button("Upload PDF", color="primary"),
                        multiple=False
                    ),
                    html.Div(id="caption-container", children=[
                        dbc.Row([
                            dbc.Col(html.H6("Caption text"), width=2, className="text-info"),
                            dbc.Col(html.H6("Page (0=all)"), width=2, className="text-info"),
                            dbc.Col(html.H6("X"), width=2, className="text-info"),
                            dbc.Col(html.H6("Y"), width=2, className="text-info"),
                            dbc.Col(html.H6("Font"), width=2, className="text-info"),
                            dbc.Col(html.H6("Size"), width=2, className="text-info"),
                        ], className="g-2 mb-1"),                        
                        dbc.Row([
                            dbc.Col(dcc.Input(id={'type': 'caption-text', 'index': 0},
                                              type='text', placeholder="Caption text"), width=2),
                            dbc.Col(dcc.Input(id={'type': 'page-num', 'index': 0},
                                              type='number', value=0, placeholder="Page (0=all)"), width=2),
                            dbc.Col(dcc.Input(id={'type': 'coord-x', 'index': 0},
                                              type='number', value=100, placeholder="X"), width=2),
                            dbc.Col(dcc.Input(id={'type': 'coord-y', 'index': 0},
                                              type='number', value=100, placeholder="Y"), width=2),
                            dbc.Col(dcc.Dropdown(
                                id={'type': 'font-family', 'index': 0},
                                options=[
                                    {'label': 'Helvetica', 'value': 'Helvetica'},
                                    {'label': 'Times New Roman', 'value': 'Times-Roman'},
                                    {'label': 'Courier', 'value': 'Courier'}
                                ],
                                value='Helvetica',
                                clearable=False
                            ), width=2),
                            dbc.Col(dcc.Input(id={'type': 'font-size', 'index': 0},
                                              type='number', value=12, placeholder="Size"), width=2),
                        ], className="g-2", id={'type': 'caption-row', 'index': 0})
                    ], className="mt-3"),

                    dbc.Button("➕ Add another caption", id="add-caption", n_clicks=0, color="success", className="mt-3")
                ])
            ], className="mb-4")
        ]),

        dbc.Tab(label="Preview & Download", tab_id="preview", children=[
            dbc.Card([
                dbc.CardBody([
                    dbc.Button("Preview PDF", id="preview-btn", color="info", className="mb-3"),
                    html.Div(id='pdf-preview', style={'margin': '10px 0',
                                                      'border': '1px solid #666',
                                                      'padding': '10px',
                                                      'backgroundColor': '#222'}),
                    dbc.Button("Download PDF", id="accept-btn", color="warning", className="mt-3"),
                    dcc.Download(id="download-pdf")
                ])
            ])
        ])
    ], active_tab="upload")

], fluid=True)

# Overlay multiple captions
def overlay_text_on_pdf(pdf_bytes, captions):
    try:
        existing_pdf = PdfReader(io.BytesIO(pdf_bytes))
        writer = PdfWriter()

        for idx, page in enumerate(existing_pdf.pages, start=1):
            for cap in captions:
                if cap["page"] == 0 or idx == cap["page"]:
                    packet = BytesIO()
                    can = canvas.Canvas(packet)
                    can.setFont(cap["font"], cap["size"])
                    can.drawString(cap["x"], cap["y"], cap["text"])
                    can.save()
                    packet.seek(0)
                    overlay_pdf = PdfReader(packet)
                    page.merge_page(overlay_pdf.pages[0])
            writer.add_page(page)

        output = BytesIO()
        writer.write(output)
        return output.getvalue()
    except Exception as e:
        print(f"Error overlaying text: {e}")
        raise

# Convert PDF -> PNG preview
def pdf_to_png_preview(pdf_bytes):
    try:
        pages = convert_from_bytes(pdf_bytes, dpi=150)
        imgs = []
        for page in pages:
            buffer = BytesIO()
            page.save(buffer, format="PNG")
            encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
            imgs.append(html.Img(src=f"data:image/png;base64,{encoded}",
                                 style={"width": "100%", "margin-bottom": "10px"}))
        return imgs
    except Exception as e:
        return f"Error generating preview: {e}"

# Store uploaded PDF
@app.callback(
    Output('pdf-preview', 'children', allow_duplicate=True),
    Input('upload-pdf', 'contents'),
    prevent_initial_call=True
)
def store_pdf(contents):
    if contents is None:
        return "No PDF uploaded."
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        pdf_storage['original'] = decoded
        return dbc.Alert("✅ PDF uploaded successfully.", color="success")
    except Exception as e:
        return dbc.Alert(f"❌ Error uploading PDF: {e}", color="danger")

# Add caption row
@app.callback(
    Output("caption-container", "children"),
    Input("add-caption", "n_clicks"),
    State("caption-container", "children"),
    prevent_initial_call=True
)
def add_caption_row(n_clicks, children):
    new_index = len(children)
    new_row = dbc.Row([
        dbc.Col(dcc.Input(id={'type': 'caption-text', 'index': new_index},
                          type='text', placeholder="Caption text"), width=2),
        dbc.Col(dcc.Input(id={'type': 'page-num', 'index': new_index},
                          type='number', value=0, placeholder="Page"), width=2),
        dbc.Col(dcc.Input(id={'type': 'coord-x', 'index': new_index},
                          type='number', value=100, placeholder="X"), width=2),
        dbc.Col(dcc.Input(id={'type': 'coord-y', 'index': new_index},
                          type='number', value=100, placeholder="Y"), width=2),
        dbc.Col(dcc.Dropdown(
            id={'type': 'font-family', 'index': new_index},
            options=[
                {'label': 'Helvetica', 'value': 'Helvetica'},  
                {'label': 'Times New Roman', 'value': 'Times-Roman'},
                {'label': 'Courier', 'value': 'Courier'}
            ],
            value='Helvetica',
            clearable=False
        ), width=2),
        dbc.Col(dcc.Input(id={'type': 'font-size', 'index': new_index},
                          type='number', value=12, placeholder="Size"), width=2),
    ], className="g-2", id={'type': 'caption-row', 'index': new_index})
    children.append(new_row)
    return children

# Preview
@app.callback(
    Output('pdf-preview', 'children'),
    Input('preview-btn', 'n_clicks'),
    State({'type': 'caption-text', 'index': ALL}, 'value'),
    State({'type': 'page-num', 'index': ALL}, 'value'),
    State({'type': 'coord-x', 'index': ALL}, 'value'),
    State({'type': 'coord-y', 'index': ALL}, 'value'),
    State({'type': 'font-family', 'index': ALL}, 'value'),
    State({'type': 'font-size', 'index': ALL}, 'value'),
    prevent_initial_call=True
)
def generate_preview(n_clicks, texts, pages, xs, ys, fonts, sizes):
    if not n_clicks or 'original' not in pdf_storage:
        return dbc.Alert("Upload a PDF and click Preview.", color="warning")
    try:
        captions = []
        for t, p, x, y, f, s in zip(texts, pages, xs, ys, fonts, sizes):
            captions.append({
                "text": t or "",
                "page": p or 0,
                "x": x or 100,
                "y": y or 100,
                "font": f or "Helvetica",
                "size": s or 12
            })
        pdf_bytes = overlay_text_on_pdf(pdf_storage['original'], captions)
        pdf_storage['preview'] = pdf_bytes
        return pdf_to_png_preview(pdf_bytes)
    except Exception as e:
        return dbc.Alert(f"❌ Error generating preview: {e}", color="danger")

# Download
@app.callback(
    Output('download-pdf', 'data'),
    Input('accept-btn', 'n_clicks'),
    prevent_initial_call=True
)
def download_pdf(n_clicks):
    if 'preview' in pdf_storage:
        return dcc.send_bytes(pdf_storage['preview'], "captioned.pdf")
    return None

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
