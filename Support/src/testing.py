import pandas as pd
from utils import *


df = pd.read_sql('select * from quarantine_customer_support', silver_con)

print(df)