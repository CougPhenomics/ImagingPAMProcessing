import numpy as np
import pandas as pd


def strip_dfwhitespace(df):
    '''
    Iterate through all columns of a dataframe and strip whitespace from fields
    '''

    df = df.copy()
    for c in df.columns:
        if df[c].dtype == np.object:
            df[c] = pd.core.strings.str_strip(df[c])
        df = df.rename(columns={c: c.strip()})
    return df
