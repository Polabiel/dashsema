import base64
import io
import pandas as pd
import dash
from dash import html, dcc, dash_table  # Adicionado dash_table
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
    'title': {'font': {'size': 20, 'color': COLORS['primary']}}
}

# Atualizar parse_contents para corrigir warning de datas
def parse_contents(contents):
    """Função para processar o arquivo carregado"""
    try:
        _content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_csv(
            io.StringIO(decoded.decode('utf-8')),
            parse_dates=['DATA', 'DATAFINALIZACAO', 'DATAULTIMAMENSAGEM'],
            dayfirst=True
        )
        return df, None
    except Exception as e:
        return None, f'Erro ao processar arquivo: {str(e)}'

def atualizar_graficos(df):
    """
    Função para atualizar os gráficos com base no DataFrame
    Args:
        df: DataFrame com os dados processados
    Returns:
        Tupla com os gráficos atualizados
    """
    # Preparação dos dados
    df['DATA'] = pd.to_datetime(df['DATA'])
    df['DATAFINALIZACAO'] = pd.to_datetime(df['DATA'])
    df['TEMPO_ATENDIMENTO'] = (df['DATAFINALIZACAO'] - df['DATA']).dt.total_seconds() / 3600

    # Gráfico de Status
    status_df = df['STATUS'].value_counts().reset_index()
    status_df.columns = ['Status', 'Quantidade']
    fig_status = px.bar(
        status_df,
        x='Status',
        y='Quantidade',
        title='Distribuição de Status'
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

    # Gráfico Tags
    tags_df = pd.Series([x.strip() for tags in df['TAGS'].dropna() for x in tags.split(',')]).value_counts().head(10).reset_index()
    tags_df.columns = ['Tag', 'Quantidade']
    fig_tags = px.bar(
        tags_df,
        x='Tag',
        y='Quantidade', 
        title='Tags',
        labels={'Tag': 'Tags', 'Quantidade': 'Número de Ocorrências'}
    )

    # Gráfico de Colaboradores
    colaboradores_df = df['ATENDENTE'].value_counts().head(10).reset_index()
    colaboradores_df.columns = ['Colaborador', 'Quantidade']
    fig_atendentes = px.bar(
        colaboradores_df,
        x='Colaborador',
        y='Quantidade',
        title='Distribuição dos Colaboradores'
    )

    # KPIs
    kpi_fig = go.Figure()
    kpi_fig.add_trace(go.Indicator(
        mode="number",
        value=len(df),
        title="Total de Atendimentos",
        domain={'row': 0, 'column': 0}
    ))

    # Atualizar layouts
    for fig in [fig_status, fig_dept, fig_timeline, fig_tags, fig_atendentes, kpi_fig]:
        fig.update_layout(**GRAPH_STYLE)

    return fig_status, fig_dept, fig_timeline, fig_tags, fig_atendentes, kpi_fig

# Adicionar função para buscar foto do GitHub
def get_github_avatar():
    try:
        response = requests.get('https://api.github.com/users/polabiel')
        if response.status_code == 200:
            return response.json()['avatar_url']
        return None
    except requests.exceptions.RequestException:
        return None

def criar_tabela_followup(df):
    """
    Cria tabela de follow-up baseada nos dados do CSV
    """
    # Converter datas
    df['DATAULTIMAMENSAGEM'] = pd.to_datetime(df['DATAULTIMAMENSAGEM'], format='%d/%m/%Y %H:%M')
    df['DATA'] = pd.to_datetime(df['DATA'], format='%d/%m/%Y %H:%M')
    
    # Encontrar última interação por número
    followup_df = df.groupby(['NUMERO', 'NOME', 'STATUS']).agg({
        'DATAULTIMAMENSAGEM': 'max',
        'DATA': 'min'  # Data de criação do atendimento
    }).reset_index()
    
    # Encontrar data mais recente no dataset
    data_mais_recente = df['DATAULTIMAMENSAGEM'].max()
    
    # Calcular dias sem contato
    followup_df['DIAS_SEM_CONTATO'] = (data_mais_recente - followup_df['DATAULTIMAMENSAGEM']).dt.days
    
    # Adicionar informação de tempo total do atendimento
    followup_df['DIAS_TOTAL'] = (data_mais_recente - followup_df['DATA']).dt.days
    
    # Formatar datas para exibição
    followup_df['DATAULTIMAMENSAGEM'] = followup_df['DATAULTIMAMENSAGEM'].dt.strftime('%d/%m/%Y %H:%M')
    followup_df['DATA'] = followup_df['DATA'].dt.strftime('%d/%m/%Y %H:%M')
    
    # Criar tabela Dash
    table = dash_table.DataTable(
        data=followup_df.to_dict('records'),
        columns=[
            {'name': 'Nome', 'id': 'NOME'},
            {'name': 'Número', 'id': 'NUMERO'},
            {'name': 'Status', 'id': 'STATUS'},
            {'name': 'Data Início', 'id': 'DATA'},
            {'name': 'Último Contato', 'id': 'DATAULTIMAMENSAGEM'},
            {'name': 'Dias Sem Contato', 'id': 'DIAS_SEM_CONTATO'},
            {'name': 'Dias Total', 'id': 'DIAS_TOTAL'}
        ],
        style_table={'overflowX': 'auto'},
        style_cell={
            'textAlign': 'left',
            'padding': '10px',
            'backgroundColor': COLORS['card']
        },
        style_header={
            'backgroundColor': COLORS['primary'],
            'color': 'white',
            'fontWeight': 'bold'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': COLORS['background']
            },
            {
                'if': {'filter_query': '{DIAS_SEM_CONTATO} > 3'},
                'backgroundColor': '#ffebee',
                'color': '#c62828'
            }
        ],
        sort_action='native',
        filter_action='native',
        page_size=10
    )
    
    return html.Div([
        html.H3('Follow-up de Clientes',
                style={'color': COLORS['primary'], 'marginBottom': '20px'}),
        html.P(f'Dados atualizados até: {data_mais_recente.strftime("%d/%m/%Y %H:%M")}',
               style={'color': COLORS['text'], 'marginBottom': '20px'}),
        table
    ], style=CARD_STYLE)

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
            ], style={'width': '100%', **CARD_STYLE}),
            html.Div([
                dcc.Graph(id='dept-graph')
            ], style={'width': '100%', **CARD_STYLE}),
        ], style={'display': 'flex', 'flexWrap': 'wrap'}),
        
        # Timeline
        html.Div([
            dcc.Graph(id='timeline-graph')
        ], style=CARD_STYLE),
        
        # Segunda linha
        html.Div([
            html.Div([
                dcc.Graph(id='tags-graph')
            ], style={'width': '100%', **CARD_STYLE}),
            html.Div([
                dcc.Graph(id='atendentes-graph')
            ], style={'width': '100%', **CARD_STYLE}),
        ], style={'display': 'flex', 'flexWrap': 'wrap'}),
        
        # Adicionar tabela de follow-up após os gráficos
        html.Div([
            dcc.Loading(
                id="loading-followup",
                type="default",
                children=html.Div(id='followup-table')
            )
        ], style=CARD_STYLE),
        
    ], style={'padding': '20px'}),
    
    # Footer
    html.Footer([
        html.Img(
            src=get_github_avatar() or 'https://github.com/polabiel.png',
            style={
                'width': '40px',
                'height': '40px',
                'borderRadius': '100%',
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

# Atualizar callback para incluir a tabela
@app.callback(
    [Output('status-graph', 'figure'),
     Output('dept-graph', 'figure'),
     Output('timeline-graph', 'figure'),
     Output('tags-graph', 'figure'),
     Output('atendentes-graph', 'figure'),
     Output('kpi-indicators', 'figure'),
     Output('followup-table', 'children'),
     Output('output-message', 'children')],
    [Input('upload-data', 'contents')],
    [State('upload-data', 'filename')]
)
def update_dashboard(contents, filename):
    if contents is None:
        return [dash.no_update] * 8
    
    try:
        df, error_message = parse_contents(contents)
        if error_message:
            return [dash.no_update] * 7 + [error_message]
        
        # Gerar gráficos e análises
        fig_status, fig_dept, fig_timeline, fig_tags, fig_atendentes, kpi_fig = atualizar_graficos(df)
        followup_table = criar_tabela_followup(df)
        
        return [
            fig_status,
            fig_dept,
            fig_timeline,
            fig_tags,
            fig_atendentes,
            kpi_fig,
            followup_table,
            f'Arquivo {filename} processado com sucesso!'
        ]
        
    except Exception as e:
        return [dash.no_update] * 7 + [f'Erro ao processar arquivo: {str(e)}']

if __name__ == '__main__':
    app.run_server(debug=True)