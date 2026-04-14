import pandas as pd

df = pd.read_csv("data/processed/final_oecd.csv")

print("shape:", df.shape)
print("\ncolumns:")
print(df.columns)

print("\nmissing values:")
print(df.isna().sum())

print("\nsummary:")
print(df.describe())    