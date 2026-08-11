import pandas as pd
from utils import *


df = pd.read_sql('select count(order_status) from orders group by order_status', bronze_con)

print(df)