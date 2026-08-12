HORARIOS = {
    "principal": [
        {"hora":"06:25","origem":"Garagem"},{"hora":"06:50","origem":"RU/Residencias"},{"hora":"07:10","origem":"RU/Residencias"},{"hora":"07:25","origem":"RU/Residencias"},{"hora":"07:40","origem":"RU/Residencias"},{"hora":"07:55","origem":"RU/Residencias"},{"hora":"09:35","origem":"Garagem"},{"hora":"10:00","origem":"Garagem"},{"hora":"11:30","origem":"Garagem"},{"hora":"11:55","origem":"RU/Residencias"},{"hora":"12:20","origem":"RU/Residencias"},{"hora":"13:00","origem":"Garagem"},{"hora":"13:25","origem":"RU/Residencias"},{"hora":"13:45","origem":"RU/Residencias"},{"hora":"14:00","origem":"RU/Residencias"},{"hora":"15:35","origem":"Garagem"},{"hora":"16:00","origem":"Garagem"},{"hora":"17:30","origem":"Garagem"},{"hora":"17:55","origem":"RU/Residencias"},{"hora":"18:15","origem":"RU/Residencias"},{"hora":"20:40","origem":"Garagem"},{"hora":"21:40","origem":"Garagem"},{"hora":"22:30","origem":"Garagem"}
    ],
    "micro": [
        {"hora":"07:25","origem":"Garagem","fim":"07:40"},
        {"hora":"07:40","origem":"RU/Residencias","fim":"07:55"},
        {"hora":"07:55","origem":"RU/Residencias","fim":"08:20"},
        {"hora":"11:30","origem":"Garagem","fim":"11:55"},
        {"hora":"11:55","origem":"RU/Residencias","fim":"12:20"},
        {"hora":"12:20","origem":"RU/Residencias","fim":"12:45"}
    ]
}

PONTOS_LISTA = [
    {"id":"ru","nome":"RU / Residências","opcional":False},
    {"id":"fitotecnia","nome":"Fitotecnia","opcional":False},
    {"id":"solos_neas_florestal","nome":"Prédio de Solos / NEAS / Eng. Florestal","opcional":False},
    {"id":"pavilhao_1","nome":"Pavilhão de Aulas I","opcional":False},
    {"id":"biblioteca","nome":"Biblioteca","opcional":False},
    {"id":"pavilhao_2","nome":"Pavilhão de Aulas II","opcional":False},
    {"id":"pavilhao_engenharia","nome":"Pavilhão de Engenharia","opcional":True},
    {"id":"portao_2","nome":"Portão 2 / Tabela","opcional":False},
    {"id":"ponto_externo_1","nome":"Ponto Externo I / Alex","opcional":False},
    {"id":"ponto_externo_2","nome":"Ponto Externo II / Canãa","opcional":False},
    {"id":"portao_1","nome":"Portão 1","opcional":False},
    {"id":"torre_cotec","nome":"Torre / COTEC","opcional":True},
]
PONTOS = {p["id"]: p for p in PONTOS_LISTA}

ROTA = [
    {"ponto_id":"ru","sentido_apos":"RUA"},
    {"ponto_id":"fitotecnia","sentido_apos":"RUA"},
    {"ponto_id":"solos_neas_florestal","sentido_apos":"RUA"},
    {"ponto_id":"pavilhao_1","sentido_apos":"RUA"},
    {"ponto_id":"biblioteca","sentido_apos":"RUA"},
    {"ponto_id":"pavilhao_2","sentido_apos":"RUA"},
    {"ponto_id":"pavilhao_engenharia","sentido_apos":"RUA","opcional":True},
    {"ponto_id":"portao_2","sentido_apos":"RUA"},
    {"ponto_id":"ponto_externo_1","sentido_apos":"RUA"},
    {"ponto_id":"ponto_externo_2","sentido_apos":"RU"},
    {"ponto_id":"portao_1","sentido_apos":"RU"},
    {"ponto_id":"biblioteca","sentido_apos":"RU"},
    {"ponto_id":"torre_cotec","sentido_apos":"RU","opcional":True},
    {"ponto_id":"ru","sentido_apos":"RUA"},
]

ROTULOS_PONTOS = {
    "ru":"RU / Residências","fitotecnia":"Fitotecnia","solos_neas_florestal":"Solos / NEAS / Florestal","pavilhao_1":"Pavilhão I","biblioteca":"Biblioteca","pavilhao_2":"Pavilhão II","pavilhao_engenharia":"Pav. Engenharia","portao_2":"Portão 2","ponto_externo_1":"Ponto Externo I / Alex","ponto_externo_2":"Ponto Externo II / Canãa","portao_1":"Portão 1","torre_cotec":"Torre / COTEC"
}
