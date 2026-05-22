from aiogram.dispatcher.filters.state import State, StatesGroup

class cat_state(StatesGroup):
  c_id = State()
  c_name = State()
  
class type_state(StatesGroup):
    c_id = State()
    t_name = State()
    t_def = State()
    t_img = State() # Yangi rasm holati

class sel_state(StatesGroup):
  c_id = State()
  t_id = State()
  s_id = State()
  cuol_1 = State()
  cuol_2 = State()
  cuol_3 = State()

class img_state(StatesGroup):
  t_id = State()
  i_id = State()
  i_ulr = State()

class sale_state(StatesGroup):
    c_id = State()
    t_id = State()
    q1 = State()
    q2 = State()
    q3 = State()
    price = State()

class manage_cat_state(StatesGroup):
    c_id = State()
    c_name = State()

class manage_ty_state(StatesGroup):
    t_id = State()
    t_name = State()
    t_def = State()

class PartnerInviteState(StatesGroup):
    pending = State()