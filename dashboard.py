import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine


st.set_page_config(
    page_title="SuAperstore Dashboard",
    page_icon="",
    layout="wide"
)


DB_USER     = "postgres"
DB_PASSWORD = "ouiamouiam"
DB_HOST     = "localhost"
DB_PORT     = "5432"
DB_NAME     = "superstore_db"

@st.cache_data  
def load_data():
    """Load and merge all tables from PostgreSQL."""
    engine = create_engine(
        f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

 
    orders        = pd.read_sql("SELECT * FROM orders", engine)
    order_details = pd.read_sql("SELECT * FROM order_details", engine)
    products      = pd.read_sql("SELECT * FROM products", engine)
    customers     = pd.read_sql("SELECT * FROM customers", engine)
    categories    = pd.read_sql("SELECT * FROM categories", engine)
    regions       = pd.read_sql("SELECT * FROM regions", engine)


    df = order_details.merge(orders,     on="order_id",    how="left")
    df = df.merge(products,              on="product_id",  how="left")
    df = df.merge(categories,            on="category_id", how="left")
    df = df.merge(customers,             on="customer_id", how="left")
    df = df.merge(regions,               on="postal_code", how="left")

    df["order_date"] = pd.to_datetime(df["order_date"])
    df["ship_date"]  = pd.to_datetime(df["ship_date"])

   
    df["year"]       = df["order_date"].dt.year
    df["month"]      = df["order_date"].dt.month
    df["year_month"] = df["order_date"].dt.to_period("M").astype(str)

   
    df["profit_margin"] = (df["profit"] / df["sales"].replace(0, np.nan)) * 100

    return df


try:
    df = load_data()
except Exception as e:
    st.error(f" Could not connect to PostgreSQL: {e}")
    st.info("Please update DB_USER, DB_PASSWORD, DB_HOST, DB_PORT and DB_NAME in dashboard.py")
    st.stop()


st.sidebar.title(" Filters")
st.sidebar.markdown("Use the filters below to explore the data.")

all_regions = sorted(df["region"].dropna().unique().tolist())
selected_regions = st.sidebar.multiselect(
    "Region",
    options=all_regions,
    default=all_regions  
)

all_categories = sorted(df["category_name"].dropna().unique().tolist())
selected_categories = st.sidebar.multiselect(
    "Category",
    options=all_categories,
    default=all_categories
)

all_years = sorted(df["year"].dropna().unique().tolist())
selected_years = st.sidebar.multiselect(
    "Year",
    options=all_years,
    default=all_years
)

filtered_df = df[
    df["region"].isin(selected_regions) &
    df["category_name"].isin(selected_categories) &
    df["year"].isin(selected_years)
]


if filtered_df.empty:
    st.warning(" No data matches the selected filters. Please adjust your selection.")
    st.stop()


st.title(" Superstore Sales Dashboard")
st.markdown(f"Showing **{filtered_df.shape[0]:,}** records based on current filters.")
st.markdown("---")


st.subheader(" Key Performance Indicators")

col1, col2, col3, col4 = st.columns(4)

total_sales       = filtered_df["sales"].sum()
total_profit      = filtered_df["profit"].sum()
avg_margin        = filtered_df["profit_margin"].mean()
total_orders      = filtered_df["order_id"].nunique()

col1.metric(" Total Sales",       f"${total_sales:,.0f}")
col2.metric(" Total Profit",      f"${total_profit:,.0f}")
col3.metric(" Avg Profit Margin", f"{avg_margin:.1f}%")
col4.metric(" Total Orders",      f"{total_orders:,}")

st.markdown("---")


st.subheader(" Monthly Sales Trend")

monthly = (filtered_df.groupby("year_month")["sales"]
                       .sum()
                       .reset_index()
                       .sort_values("year_month"))

fig1, ax1 = plt.subplots(figsize=(12, 4))
ax1.plot(monthly["year_month"], monthly["sales"],
         marker="o", linewidth=2, markersize=4, color="steelblue")
ax1.set_xlabel("Month")
ax1.set_ylabel("Total Sales ($)")
ax1.set_title("Monthly Sales Trend")
plt.xticks(rotation=45, ha="right", fontsize=8)
plt.tight_layout()
st.pyplot(fig1)
plt.close()

st.markdown("---")


st.subheader(" Performance by Category")

col_a, col_b = st.columns(2)


with col_a:
    sales_cat = (filtered_df.groupby("category_name")["sales"]
                             .sum()
                             .reset_index()
                             .sort_values("sales", ascending=False))

    fig2, ax2 = plt.subplots(figsize=(6, 4))
    bars = ax2.bar(sales_cat["category_name"], sales_cat["sales"],
                   color=["#66c2a5", "#fc8d62", "#8da0cb"])
    for bar in bars:
        ax2.text(bar.get_x() + bar.get_width() / 2,
                 bar.get_height() + 500,
                 f"${bar.get_height():,.0f}",
                 ha="center", fontsize=9)
    ax2.set_title("Sales by Category")
    ax2.set_xlabel("Category")
    ax2.set_ylabel("Total Sales ($)")
    plt.tight_layout()
    st.pyplot(fig2)
    plt.close()

with col_b:
    profit_cat = (filtered_df.groupby("category_name")["profit"]
                              .sum()
                              .reset_index()
                              .sort_values("profit", ascending=False))

    fig3, ax3 = plt.subplots(figsize=(6, 4))
    colors = ["green" if p > 0 else "red" for p in profit_cat["profit"]]
    ax3.bar(profit_cat["category_name"], profit_cat["profit"], color=colors)
    ax3.set_title("Profit by Category")
    ax3.set_xlabel("Category")
    ax3.set_ylabel("Total Profit ($)")
    plt.tight_layout()
    st.pyplot(fig3)
    plt.close()

st.markdown("---")

st.subheader(" Top 10 Products by Sales")

top10 = (filtered_df.groupby("product_name")["sales"]
                     .sum()
                     .reset_index()
                     .sort_values("sales", ascending=True)
                     .tail(10))

fig4, ax4 = plt.subplots(figsize=(10, 5))
ax4.barh(top10["product_name"], top10["sales"], color="coral")
ax4.set_xlabel("Total Sales ($)")
ax4.set_title("Top 10 Products by Sales")
plt.tight_layout()
st.pyplot(fig4)
plt.close()

st.markdown("---")


st.subheader(" Sales Heatmap: Region × Category")

pivot = filtered_df.pivot_table(
    index="region", columns="category_name",
    values="sales", aggfunc="sum"
).fillna(0)

fig5, ax5 = plt.subplots(figsize=(8, 4))
sns.heatmap(pivot, annot=True, fmt=".0f", cmap="YlOrRd", ax=ax5, linewidths=0.5)
ax5.set_title("Sales by Region and Category")
ax5.set_xlabel("Category")
ax5.set_ylabel("Region")
plt.tight_layout()
st.pyplot(fig5)
plt.close()

st.markdown("---")


st.subheader(" Profit Distribution")

fig6, ax6 = plt.subplots(figsize=(9, 4))
sns.histplot(filtered_df["profit"], bins=60, kde=True, color="mediumseagreen", ax=ax6)
mean_profit = filtered_df["profit"].mean()
ax6.axvline(mean_profit, color="red", linestyle="--",
            label=f"Mean: ${mean_profit:.0f}")
ax6.set_xlabel("Profit ($)")
ax6.set_ylabel("Count")
ax6.set_title("Distribution of Profit")
ax6.legend()
plt.tight_layout()
st.pyplot(fig6)
plt.close()

st.markdown("---")
st.caption(" Superstore Analytics Dashboard — Built with Streamlit · Data from PostgreSQL")
