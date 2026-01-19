import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# -----------------------------------
# PAGE SETUP
# -----------------------------------
st.set_page_config(page_title="Chadorkart Inventory", layout="wide")
st.title("📦 Chadorkart Inventory – Complete Inventory Dashboard")

# -----------------------------------
# FILE UPLOAD
# -----------------------------------
inv_file = st.file_uploader("Upload INVENTORY CSV", type=["csv"])
sales_file = st.file_uploader("Upload SALES / ORDERS CSV", type=["csv"])

if inv_file and sales_file:

    # -----------------------------------
    # LOAD DATA
    # -----------------------------------
    inv = pd.read_csv(inv_file)
    sales = pd.read_csvsales = pd.read_csv(sales_file)

    inv.columns = inv.columns.str.strip()
    sales.columns = sales.columns.str.strip()

    # -----------------------------------
    # DATE PARSE
    # -----------------------------------
    sales["Uniware Created At"] = pd.to_datetime(
        sales["Uniware Created At"], errors="coerce"
    )

    # -----------------------------------
    # SPLIT Seller SKUs
    # -----------------------------------
    sales["Seller SKUs"] = sales["Seller SKUs"].astype(str)
    sales["Seller SKUs"] = (
        sales["Seller SKUs"]
        .str.replace("|", ",", regex=False)
        .str.split(",")
    )
    sales = sales.explode("Seller SKUs")
    sales["Seller SKUs"] = sales["Seller SKUs"].str.strip()

    # -----------------------------------
    # FIX CORRUPTED SKUs USING Products
    # -----------------------------------
    def is_corrupted_sku(sku):
        if sku.startswith("vof-"):
            return True
        if sku.count("-") > 1:
            return True
        if len(sku) > 20:
            return True
        return False

    sales["Final SKU"] = sales.apply(
        lambda x: x["Products"] if is_corrupted_sku(x["Seller SKUs"]) else x["Seller SKUs"],
        axis=1
    )

    sales["Final SKU"] = sales["Final SKU"].astype(str).str.strip()
    sales = sales[sales["Final SKU"] != ""]

    # -----------------------------------
    # SALES COUNTS
    # -----------------------------------
    total_sales = (
        sales.groupby("Final SKU")
        .size()
        .reset_index(name="Total Sold")
    )

    # -----------------------------------
    # SALES TREND (7 / 30 DAYS)
    # -----------------------------------
    today = datetime.now()
    last_7_days = today - timedelta(days=7)
    last_30_days = today - timedelta(days=30)

    sales_7d = (
        sales[sales["Uniware Created At"] >= last_7_days]
        .groupby("Final SKU")
        .size()
        .reset_index(name="Sold Last 7 Days")
    )

    sales_30d = (
        sales[sales["Uniware Created At"] >= last_30_days]
        .groupby("Final SKU")
        .size()
        .reset_index(name="Sold Last 30 Days")
    )

    # -----------------------------------
    # MASTER SKU LIST
    # -----------------------------------
    inventory_skus = inv[["Sku Code", "Available (ATP)"]].copy()
    inventory_skus.rename(columns={"Sku Code": "SKU"}, inplace=True)

    sales_skus = total_sales[["Final SKU"]].copy()
    sales_skus.rename(columns={"Final SKU": "SKU"}, inplace=True)

    master_skus = pd.concat(
        [inventory_skus[["SKU"]], sales_skus],
        ignore_index=True
    ).drop_duplicates()

    # -----------------------------------
    # MERGE INVENTORY
    # -----------------------------------
    data = master_skus.merge(
        inventory_skus,
        on="SKU",
        how="left"
    )
    data["Available (ATP)"] = data["Available (ATP)"].fillna(0)

    # -----------------------------------
    # MERGE SALES
    # -----------------------------------
    data = data.merge(
        total_sales,
        left_on="SKU",
        right_on="Final SKU",
        how="left"
    )
    data = data.merge(
        sales_7d,
        left_on="SKU",
        right_on="Final SKU",
        how="left"
    )
    data = data.merge(
        sales_30d,
        left_on="SKU",
        right_on="Final SKU",
        how="left"
    )

    data.fillna(0, inplace=True)
    data.rename(columns={"SKU": "Sku Code"}, inplace=True)

    # -----------------------------------
    # DEAD STOCK (RESTORED)
    # -----------------------------------
    data["Dead Stock"] = (
        (data["Sold Last 30 Days"] == 0) &
        (data["Available (ATP)"] > 0)
    )

    # -----------------------------------
    # STOCK TO ORDER (FINAL LOGIC)
    # -----------------------------------
    data["Stock To Order"] = (
        data["Total Sold"] - data["Available (ATP)"]
    ).clip(lower=0)

    # -----------------------------------
    # 🔥 TOP SELLING SKUs
    # -----------------------------------
    st.subheader("🔥 Top Selling SKUs (Highest → Lowest)")
    st.dataframe(
        data.sort_values("Total Sold", ascending=False)[[
            "Sku Code", "Total Sold", "Available (ATP)"
        ]]
    )

    # -----------------------------------
    # 📅 SALES TREND
    # -----------------------------------
    st.subheader("📅 SKU Sales Trend (Last 7 / 30 Days)")
    st.dataframe(
        data.sort_values("Sold Last 7 Days", ascending=False)[[
            "Sku Code", "Sold Last 7 Days", "Sold Last 30 Days"
        ]]
    )

    # -----------------------------------
    # 📦 STOCK TO ORDER
    # -----------------------------------
    st.subheader("📦 Stock To Order (Total Sold − Available Stock)")
    st.dataframe(
        data[data["Stock To Order"] > 0]
        .sort_values("Stock To Order", ascending=False)[[
            "Sku Code", "Total Sold", "Available (ATP)", "Stock To Order"
        ]]
    )

    # -----------------------------------
    # 🧊 DEAD STOCK TABLE
    # -----------------------------------
    st.subheader("🧊 Dead Stock (No Sales in Last 30 Days)")
    st.dataframe(
        data[data["Dead Stock"]]
        .sort_values("Available (ATP)", ascending=False)[[
            "Sku Code", "Available (ATP)", "Sold Last 30 Days"
        ]]
    )

    # -----------------------------------
    # 📊 SUMMARY
    # -----------------------------------
    st.subheader("📊 Summary")
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total SKUs", data.shape[0])
    col2.metric("Total Sales (Units)", int(data["Total Sold"].sum()))
    col3.metric("SKUs To Order", (data["Stock To Order"] > 0).sum())
    col4.metric("Total Units To Order", int(data["Stock To Order"].sum()))

    # -----------------------------------
    # 🛒 SALES BY CHANNEL
    # -----------------------------------
    st.subheader("🛒 Total Sales by Channel")
    channel_sales = (
        sales.groupby("Channel")
        .size()
        .reset_index(name="Total Sales")
        .sort_values("Total Sales", ascending=False)
    )
    st.dataframe(channel_sales)

else:
    st.info("⬆️ Upload both Inventory & Sales CSV files to continue")