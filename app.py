import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from dash import Dash, dcc, html, Input, Output, State, callback_context
import base64
import io

# Define the time to seconds function
def time_to_seconds(time_str):
    if pd.isna(time_str) or time_str == '00:00:00':
        return np.nan
    parts = time_str.split(':')
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + int(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + int(s)
    else:
        return int(parts[0])

# Function to process the uploaded file
def process_data(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename:
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        else:
            return None, "Unsupported file type. Please upload a CSV file."
    except Exception as e:
        return None, str(e)

    # Convert time strings to seconds
    time_columns = ['Swim', 'T1', 'Bike', 'T2', 'Run', 'Total Time']
    for col in time_columns:
        df[col] = df[col].apply(time_to_seconds)

    # Calculate cumulative times
    segments = ['Swim', 'T1', 'Bike', 'T2', 'Run']
    df['Swim_Cum'] = df['Swim']
    for i in range(1, len(segments)):
        df[f'{segments[i]}_Cum'] = df[f'{segments[i-1]}_Cum'] + df[segments[i]]

    return df, None

# Create the app
app = Dash(__name__)

# Define custom CSS for Apple-inspired styling
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            @font-face {
                font-family: 'SF Pro Display';
                src: url('https://applesocial.s3.amazonaws.com/assets/styles/fonts/sanfrancisco/sanfranciscodisplay-regular-webfont.woff');
            }
            body {
                font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif;
                background-color: #f5f5f7;
                margin: 0;
                padding: 20px;
                color: #1d1d1f;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background-color: white;
                border-radius: 18px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                padding: 30px;
            }
            h1 {
                font-weight: 800;
                font-size: 38px;
                margin-bottom: 0px;
            }
            h2 {
                font-weight: 300;
                font-size: 22px;
                margin-bottom: 30px;
                color: #86868b;
            }
            .upload-box {
                border: 2px dashed #86868b;
                border-radius: 10px;
                padding: 20px;
                text-align: center;
                margin-bottom: 20px;
                cursor: pointer;
                transition: background-color 0.3s;
            }
            .upload-box:hover {
                background-color: #f0f0f0;
            }
            .radio-items {
                display: flex;
                justify-content: flex-start;
                margin-bottom: 20px;
            }
            .radio-items .form-check {
                margin-right: 30px;
            }
            .btn-primary {
                background-color: #0071e3;
                border: none;
                padding: 10px 20px;
                border-radius: 20px;
                color: white;
                font-weight: 500;
                font-size: 16px;
                transition: background-color 0.3s;
                cursor: pointer;
                margin-bottom: 10px;
            }
            .btn-primary:hover {
                background-color: #0077ed;
            }
            .btn-primary:disabled {
                background-color: #999999;
                cursor: not-allowed;
            }
            #output-data-upload {
                font-size: 14px;
                color: #86868b;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Define the layout
app.layout = html.Div([
    html.Div([
        html.H1("Triathlon Race Simulator"),
        html.H2("Visualize and analyze triathlon race data with ease"),
        html.Div([
            dcc.Upload(
                id='upload-data',
                children=html.Div([
                    'Drag and Drop or ',
                    html.A('Select Files')
                ]),
                className='upload-box'
            ),
        ]),
        html.Div([
            dcc.RadioItems(
                id='calculation-mode',
                options=[
                    {'label': 'Position-based', 'value': 'position'},
                    {'label': 'Time gap-based', 'value': 'time_gap'}
                ],
                value=None,
                className='radio-items',
                inputStyle={"marginRight": "5px"}
            ),
        ]),
        html.Button('Visualize', id='visualize-button', className='btn-primary', disabled=True),
        html.Div(id='output-data-upload'),
        dcc.Graph(id='race-plot', style={'height': '600px', 'display': 'none'}),
        html.Div(id='hover-data')
    ], className='container')
])

# Callback to enable/disable the Visualize button and update the upload message
@app.callback(
    Output('visualize-button', 'disabled'),
    Output('output-data-upload', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def update_button_state_and_message(contents, filename):
    if contents is None:
        return True, "No file uploaded yet."
    else:
        return False, f"File '{filename}' uploaded successfully. Select a calculation mode and click 'Visualize' to process and display the data."

# Update the main callback
@app.callback(
    Output('race-plot', 'figure'),
    Output('race-plot', 'style'),
    Input('visualize-button', 'n_clicks'),
    Input('calculation-mode', 'value'),
    Input('race-plot', 'hoverData'),
    State('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def update_graph(n_clicks, calculation_mode, hoverData, contents, filename):
    ctx = callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if contents is None or calculation_mode is None:
        return go.Figure(), {'display': 'none'}

    df, error_message = process_data(contents, filename)
    if error_message:
        return go.Figure(), {'display': 'none'}

    if triggered_id == 'visualize-button':
        return create_figure(df, calculation_mode, filename), {'display': 'block', 'height': '600px'}
    elif triggered_id == 'race-plot' and hoverData is not None:
        hovered_name = hoverData['points'][0]['text'].split('<br>')[0]
        return create_figure(df, calculation_mode, filename, hovered_athlete=hovered_name), {'display': 'block', 'height': '600px'}
    else:
        return go.Figure(), {'display': 'none'}

# Create the figure function
def create_figure(df, calculation_mode, filename, hovered_athlete=None):
    fig = go.Figure()

    segments = ['Swim', 'T1', 'Bike', 'T2', 'Run']
    x_values = [0, 0.5, 0.6, 2.0, 2.1, 3.0]
    x_labels = ['Start'] + segments

    if calculation_mode == 'position':
        for split in [f'{seg}_Cum' for seg in segments]:
            df[f'{split}_Rank'] = df[split].rank(method='min', na_option='bottom')
        max_rank = df[[f'{split}_Cum_Rank' for split in segments]].max().max()
        y_axis_title = 'Rank'
    else:  # time_gap mode
        for split in [f'{seg}_Cum' for seg in segments]:
            leader_time = df[split].min()
            df[f'{split}_Gap'] = df[split] - leader_time
        max_gap = df[[f'{seg}_Cum_Gap' for seg in segments]].max().max()
        y_axis_title = 'Time Gap to Leader (seconds)'
        
        df = df[df['Run_Cum'].notna()]

    df = df.sort_values('Position', na_position='last')

    # Create a color palette
    color_palette = px.colors.qualitative.Bold

    for i, (_, athlete) in enumerate(df.iterrows()):
        name = f"{athlete['Athlete First Name']} {athlete['Athlete Last Name']}"
        y_values = [0]
        athlete_x_values = [x_values[0]]
        for j, seg in enumerate(segments):
            if calculation_mode == 'position':
                value = athlete[f'{seg}_Cum_Rank']
            else:
                value = athlete[f'{seg}_Cum_Gap']
            if pd.isna(value):
                break
            y_values.append(value)
            athlete_x_values.append(x_values[j+1])

        if calculation_mode == 'position' and len(y_values) < len(segments) + 1:
            y_values.append(max_rank)
            athlete_x_values.append(athlete_x_values[-1])

        opacity = 1 if hovered_athlete == name else 0.2 if hovered_athlete else 0.6

        hover_text = [f"{name}<br>Segment: {seg}<br>{y_axis_title}: {y:.0f}" for seg, y in zip(['Start'] + segments, y_values)]

        fig.add_trace(go.Scatter(
            x=athlete_x_values,
            y=y_values,
            mode='lines+markers',
            name=name,
            text=hover_text,
            hoverinfo='text',
            line=dict(width=2, color=color_palette[i % len(color_palette)]),
            marker=dict(size=8, color=color_palette[i % len(color_palette)]),
            opacity=opacity
        ))

    fig.update_layout(
        title=f'Visualizing: {filename}',
        title_font_size=24,
        title_font_family="SF Pro Display, -apple-system, BlinkMacSystemFont, sans-serif",
        xaxis=dict(
            title='Segment',
            tickmode='array',
            tickvals=x_values,
            ticktext=x_labels,
            tickangle=45,
            title_font_size=16,
            tickfont_size=14,
        ),
        yaxis=dict(
            title=y_axis_title,
            autorange='reversed' if calculation_mode == 'position' else True,
            title_font_size=16,
            tickfont_size=14,
        ),
        font_family="SF Pro Display, -apple-system, BlinkMacSystemFont, sans-serif",
        hovermode='closest',
        showlegend=False,
        height=600,
        plot_bgcolor='rgba(240,240,240,0.8)',  # Light grey background
        paper_bgcolor='white',
        margin=dict(l=50, r=50, t=80, b=50),
    )

    if calculation_mode == 'time_gap':
        fig.update_layout(yaxis_range=[max_gap, 0])

    return fig

# Run the app
if __name__ == '__main__':
    app.run_server(debug=False)