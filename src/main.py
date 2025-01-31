import base64
import io
import pandas as pd
import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
import requests

# Cores e estilos
COLORS = {
    'background': '#f8f9fa',
    'card': '#ffffff',
    'primary': '#2C3E50',
    'secondary': '#3498DB',
    'text': '#2c3e50',
    'border': '#e9ecef'
}

# Estilos comuns
CARD_STYLE = {
    'backgroundColor': COLORS['card'],
    'borderRadius': '8px',
    'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
    'padding': '20px',
    'margin': '10px',
    'border': f'1px solid {COLORS["border"]}'
}

# Estilo comum para os gráficos
GRAPH_STYLE = {
    'paper_bgcolor': COLORS['background'],
    'plot_bgcolor': COLORS['background'],
    'font': {'color': COLORS['text']},
    'title': {'font': {'size': 24, 'color': COLORS['primary']}}
}

def parse_contents(contents):
    """Função para processar o arquivo carregado"""
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        return df, None
    except Exception as e:
        return None, f'Erro ao processar arquivo: {str(e)}'

def atualizar_graficos(contents, filename):
    if contents is None:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, ''
    
    df, error_message = parse_contents(contents)
    if error_message:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, error_message

    # Preparação dos dados
    df['DATA'] = pd.to_datetime(df['DATA'])
    df['DATAFINALIZACAO'] = pd.to_datetime(df['DATAFINALIZACAO'])
    df['TEMPO_ATENDIMENTO'] = (df['DATAFINALIZACAO'] - df['DATA']).dt.total_seconds() / 3600

    # Gráfico de Status
    status_df = df['STATUS'].value_counts().reset_index()
    status_df.columns = ['Status', 'Quantidade']
    fig_status = px.bar(
        status_df,
        x='Status',
        y='Quantidade',
        title='Distribuição de Status',
        color='Status'
    )

    # Gráfico de Departamentos
    dept_df = df['DEPARTAMENTO'].value_counts().reset_index()
    dept_df.columns = ['Departamento', 'Quantidade']
    fig_dept = px.pie(
        dept_df,
        values='Quantidade',
        names='Departamento',
        title='Distribuição por Departamento'
    )

    # Gráfico Timeline
    timeline_df = df.groupby(df['DATA'].dt.date).size().reset_index()
    timeline_df.columns = ['Data', 'Quantidade']
    fig_timeline = px.line(
        timeline_df,
        x='Data',
        y='Quantidade',
        title='Volume de Atendimentos por Dia'
    )

    # Gráfico de Tags
    tags_series = pd.Series([x.strip() for tags in df['TAGS'].dropna() for x in tags.split(',')])
    tags_df = tags_series.value_counts().head(10).reset_index()
    tags_df.columns = ['Tag', 'Quantidade']
    fig_tags = px.bar(
        tags_df,
        x='Tag',
        y='Quantidade',
        title='Top 10 Tags'
    )

    # Gráfico de Atendentes
    atendentes_df = df['ATENDENTE'].value_counts().head(10).reset_index()
    atendentes_df.columns = ['Atendente', 'Quantidade']
    fig_atendentes = px.bar(
        atendentes_df,
        x='Atendente',
        y='Quantidade',
        title='Top 10 Atendentes'
    )

    # KPIs
    kpi_fig = go.Figure()
    kpi_fig.add_trace(go.Indicator(
        mode="number+delta",
        value=len(df),
        title="Total de Atendimentos",
        domain={'row': 0, 'column': 0}
    ))

    # Atualizar layouts
    for fig in [fig_status, fig_dept, fig_timeline, fig_tags, fig_atendentes]:
        fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            font={'color': '#333'},
            margin=dict(t=30, l=10, r=10, b=10)
        )

    return fig_status, fig_dept, fig_timeline, fig_tags, fig_atendentes, kpi_fig, \
           f'Arquivo {filename} processado com sucesso! Total de {len(df)} atendimentos.'

# Adicionar função para buscar foto do GitHub
def get_github_avatar():
    try:
        response = requests.get('https://api.github.com/users/polabiel')
        if response.status_code == 200:
            return response.json()['avatar_url']
        return None
    except:
        return None

# Layout do app
app = dash.Dash(__name__)
app.layout = html.Div([
    # Header
    html.Div([
        html.H1('Dashboard de Atendimentos',
                style={
                    'textAlign': 'center',
                    'color': COLORS['primary'],
                    'fontWeight': 'bold',
                    'padding': '20px',
                    'marginBottom': '20px'
                })
    ], style={'backgroundColor': COLORS['card'], 'marginBottom': '20px'}),
    
    # Upload
    html.Div([
        dcc.Upload(
            id='upload-data',
            children=html.Div([
                html.I(className='fas fa-upload', style={'marginRight': '10px'}),
                'Arraste e solte ou ',
                html.A('selecione um arquivo')
            ]),
            style={
                'width': '100%',
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '2px',
                'borderStyle': 'dashed',
                'borderRadius': '8px',
                'textAlign': 'center',
                'backgroundColor': COLORS['background'],
                'transition': 'border-color 0.3s',
                'cursor': 'pointer'
            }
        )
    ], style=CARD_STYLE),
    
    # Mensagem de feedback
    html.Div(id='output-message', style={'textAlign': 'center', 'margin': '20px'}),
    
    # KPIs
    html.Div([
        dcc.Graph(id='kpi-indicators')
    ], style=CARD_STYLE),
    
    # Grid de gráficos
    html.Div([
        # Primeira linha
        html.Div([
            html.Div([
                dcc.Graph(id='status-graph')
            ], style={'width': '50%', **CARD_STYLE}),
            html.Div([
                dcc.Graph(id='dept-graph')
            ], style={'width': '50%', **CARD_STYLE}),
        ], style={'display': 'flex', 'flexWrap': 'wrap'}),
        
        # Timeline
        html.Div([
            dcc.Graph(id='timeline-graph')
        ], style=CARD_STYLE),
        
        # Segunda linha
        html.Div([
            html.Div([
                dcc.Graph(id='tags-graph')
            ], style={'width': '50%', **CARD_STYLE}),
            html.Div([
                dcc.Graph(id='atendentes-graph')
            ], style={'width': '50%', **CARD_STYLE}),
        ], style={'display': 'flex', 'flexWrap': 'wrap'}),
        
        # Análise de números
        html.Div([
            html.Div(id='numeros-analysis')
        ], style=CARD_STYLE),
        
    ], style={'padding': '20px'}),
    
    # Footer
    html.Footer([
        html.Img(
            src=get_github_avatar() or 'https://github.com/polabiel.png',
            style={
                'width': '40px',
                'height': '40px',
                'borderRadius': '50%',
                'border': f'2px solid {COLORS["primary"]}'
            }
        ),
        html.Div([
            html.P(
                'Desenvolvido por Gabriel Oliveira',
                style={
                    'margin': '0',
                    'color': COLORS['text'],
                    'fontWeight': 'bold'
                }
            ),
            html.A(
                'github.com/polabiel',
                href='https://github.com/polabiel',
                target='_blank',
                style={
                    'color': COLORS['secondary'],
                    'textDecoration': 'none',
                    'fontSize': '14px'
                }
            )
        ])
    ], style={
        'backgroundColor': COLORS['card'],
        'padding': '20px',
        'textAlign': 'center',
        'borderTop': f'1px solid {COLORS["border"]}',
        'marginTop': '30px',
        'display': 'flex',
        'alignItems': 'center',
        'justifyContent': 'center',
        'gap': '15px'
    })
    
], style={
    'backgroundColor': COLORS['background'],
    'minHeight': '100vh',
    'fontFamily': '"Segoe UI", "Roboto", sans-serif',
    'display': 'flex',
    'flexDirection': 'column'
})

# Atualizar estilo dos gráficos
GRAPH_STYLE.update({
    'margin': dict(t=30, l=10, r=10, b=10),
    'font': {'family': '"Segoe UI", "Roboto", sans-serif', 'color': COLORS['text']},
    'plot_bgcolor': COLORS['card'],
    'paper_bgcolor': COLORS['card']
})

@app.callback(
    [Output('status-graph', 'figure'),
     Output('dept-graph', 'figure'),
     Output('timeline-graph', 'figure'),
     Output('tags-graph', 'figure'),
     Output('atendentes-graph', 'figure'),
     Output('kpi-indicators', 'figure'),
     Output('output-message', 'children')],
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def update_output(contents, filename):
    if contents is None:
        return [dash.no_update] * 7
    return atualizar_graficos(contents, filename)

if __name__ == '__main__':
    app.run_server(debug=True)