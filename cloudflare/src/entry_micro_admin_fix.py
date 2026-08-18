import entry as _entry_base
import entry_micro_admin as _micro_admin
from entry_micro_admin import *

# Os handlers herdados de entry.Default resolvem estes teclados no namespace
# global de entry.py. O wrapper anterior alterava apenas entry_micro_flex, por
# isso os callbacks existiam mas o botao nao era renderizado.
_entry_base.teclado_menu_com_controle = _micro_admin.teclado_menu_micro_admin
_entry_base.teclado_localizacao = _micro_admin.teclado_localizacao_micro_admin
