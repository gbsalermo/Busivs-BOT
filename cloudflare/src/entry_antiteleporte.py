import entry_admin_hub as _entry
from entry_admin_hub import *


# A camada temporal de anti-teletransporte foi desativada.
# O registro volta a depender apenas das regras estruturais da rota e dos blocos.
class BusState(_entry.BusState):
    pass


class Default(_entry.Default):
    pass
