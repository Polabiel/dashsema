import pandas as pd
import dash
from dash import dcc, html
import plotly.express as px
from dash.dependencies import Input, Output

# Função para carregar os dados
def carregar_dados(filepath):
    df = pd.read_csv(filepath, encoding="latin1", sep=";", low_memory=False)
    return df

# Inicializar o app Dash
app = dash.Dash(__name__)

# Layout do dashboard
app.layout = html.Div([
    html.H1("Dashboard de Atendimentos - UP3D"),
    
    dcc.Upload(
        id='upload-data',
        children=html.Button('Carregar Nova Planilha'),
        multiple=False
    ),
    
    dcc.Graph(id='grafico-status'),
    dcc.Graph(id='grafico-departamento')
])

# Callback para atualizar os gráficos
@app.callback(
    [Output('grafico-status', 'figure'),
     Output('grafico-departamento', 'figure')],
    [Input('upload-data', 'contents')]
)
def atualizar_graficos(contents):
    if contents is None:
        return dash.no_update
    
    df = carregar_dados('caminho_para_a_planilha.csv')  # Atualizar para caminho correto
    
    # Gráfico de status dos atendimentos
    fig_status = px.bar(df['STATUS'].value_counts().reset_index(), x='index', y='STATUS',
                        labels={'index': 'Status', 'STATUS': 'Quantidade'},
                        title='Distribuição de Status dos Atendimentos')
    
    # Gráfico de departamentos mais acionados
    fig_departamento = px.pie(df, names='DEPARTAMENTO', title='Atendimentos por Departamento')
    
    return fig_status, fig_departamento

# Rodar o servidor
if __name__ == '__main__':
    app.run_server(debug=True)