import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# -----------------------------------
# PAGE SETUP
# -----------------------------------
st.set_page_config(page_title="Chadorkart Inventory", layout="wide")
st.title("📦 The Inventory – Complete Inventory Dashboard For Chadorkart")

# -----------------------------------
# FILE UPLOAD
# -----------------------------------
inv_file = st.file_uploader("Upload UNIWARE INVENTORY CSV", type=["csv"])
sales_file = st.file_uploader("Upload UNIWARE SALES / ORDERS CSV", type=["csv"])

if inv_file and sales_file:

    # -----------------------------------
    # LOAD DATA
    # -----------------------------------
    inv = pd.read_csv(inv_file)
    sales = pd.read_csv(sales_file)

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
        sku = str(sku)
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
    # SALES COUNTS (UNCHANGED)
    # -----------------------------------
    total_sales = (
        sales.groupby("Final SKU")
        .size()
        .reset_index(name="Total Sold")
    )

    # -----------------------------------
    # MASTER SKU LIST (UNCHANGED)
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
    # MERGE INVENTORY (UNCHANGED)
    # -----------------------------------
    data = master_skus.merge(
        inventory_skus,
        on="SKU",
        how="left"
    )
    data["Available (ATP)"] = data["Available (ATP)"].fillna(0)

    # -----------------------------------
    # MERGE SALES (UNCHANGED)
    # -----------------------------------
    data = data.merge(
        total_sales,
        left_on="SKU",
        right_on="Final SKU",
        how="left"
    )

    data.fillna(0, inplace=True)
    data.rename(columns={"SKU": "Sku Code"}, inplace=True)

    # -----------------------------------
    # DEAD STOCK (UNCHANGED)
    # -----------------------------------
    data["Dead Stock"] = (
        (data["Total Sold"] == 0) &
        (data["Available (ATP)"] > 0)
    )

    # -----------------------------------
    # STOCK TO ORDER (UNCHANGED)
    # -----------------------------------
    data["Stock To Order"] = (
        data["Total Sold"] - data["Available (ATP)"]
    ).clip(lower=0)

    # -----------------------------------
    # 🔥 TOP SELLING SKUs (UNCHANGED)
    # -----------------------------------
    st.subheader("🔥 Top Selling SKUs (Highest → Lowest)")
    st.dataframe(
        data.sort_values("Total Sold", ascending=False)[[
            "Sku Code", "Total Sold", "Available (ATP)"
        ]]
    )

    # ======================================================
    # 🛒 SALES BY CHANNEL – PIVOT TABLE (ONLY NEW FEATURE)
    # ======================================================
    st.subheader("🛒 SKU Sales by Channel")

    sales["Channel"] = sales["Channel"].astype(str).str.strip()

    sku_channel_pivot = (
        sales.pivot_table(
            index="Final SKU",
            columns="Channel",
            aggfunc="size",
            fill_value=0
        )
    )

    sku_channel_pivot["Total"] = sku_channel_pivot.sum(axis=1)
    sku_channel_pivot = sku_channel_pivot.sort_values("Total", ascending=False)
    sku_channel_pivot.reset_index(inplace=True)
    sku_channel_pivot.rename(columns={"Final SKU": "Sku Code"}, inplace=True)

    st.dataframe(sku_channel_pivot)

    # -----------------------------------
    # 📦 STOCK TO ORDER (UNCHANGED)
    # -----------------------------------
    st.subheader("📦 Stock To Order (Total Sold − Available Stock)")
    st.dataframe(
        data[data["Stock To Order"] > 0]
        .sort_values("Stock To Order", ascending=False)[[
            "Sku Code", "Total Sold", "Available (ATP)", "Stock To Order"
        ]]
    )

    # -----------------------------------
    # 🧊 DEAD STOCK (UNCHANGED)
    # -----------------------------------
    st.subheader("🧊 Dead Stock (No Sales in Last 30 Days)")
    st.dataframe(
        data[data["Dead Stock"]]
        .sort_values("Available (ATP)", ascending=False)[[
            "Sku Code", "Available (ATP)", "Total Sold"
        ]]
    )

    # -----------------------------------
    # 📊 SUMMARY (UNCHANGED)
    # -----------------------------------
   
    st.subheader("🛒 Total Sales by Channel")
    channel_sales = (
        sales.groupby("Channel")
        .size()
        .reset_index(name="Total Sales")
        .sort_values("Total Sales", ascending=False)
    )
    st.dataframe(channel_sales)

    st.subheader("📊 Summary")
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total SKUs", data.shape[0])
    col2.metric("Total Sales (Units)", int(data["Total Sold"].sum()))
    col3.metric("SKUs To Order", (data["Stock To Order"] > 0).sum())
    col4.metric("Total Units To Order", int(data["Stock To Order"].sum()))

else:
    st.info("⬆️ Upload both Inventory & Sales CSV files to continue")
