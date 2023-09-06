import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import pyttsx3
from gtts import gTTS
from io import BytesIO
import base64
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image, Spacer, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

def generate_visualizations(expense_df):
    # Bar chart
    bar_chart_fig, ax = plt.subplots(figsize=(8, 6))
    sns.barplot(x="Amount", y="Category", data=expense_df, ax=ax)
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Pie chart
    pie_chart_fig, ax = plt.subplots(figsize=(8, 6))
    category_amounts = expense_df.groupby("Category")["Amount"].sum()
    ax.pie(category_amounts, labels=category_amounts.index, autopct="%1.1f%%", startangle=90)
    ax.axis("equal")
    plt.tight_layout()

    return bar_chart_fig, pie_chart_fig

def create_pdf_report(expense_df, income, total_expenses, total_balance, bar_chart_fig, pie_chart_fig):
    # Create PDF document
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    # Styles
    styles = getSampleStyleSheet()

    # Add title
    title = Paragraph("Personal Finance Manager", styles['Title'])
    content = [title, Spacer(1, 12)]

    # Table for income, expenses, and balance
    data = [
        ["Total Income", f"${income:.2f}"],
        ["Total Expenses", f"${total_expenses:.2f}"],
        ["Total Balance", f"${total_balance:.2f}"],
    ]
    table = Table(data, colWidths=[200, 100])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), "grey"),
        ("TEXTCOLOR", (0, 0), (-1, 0), (1, 1, 1)),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
    ]))
    content.append(table)
    content.append(Spacer(1, 24))

    # Add bar chart
    bar_chart_image = BytesIO()
    bar_chart_fig.savefig(bar_chart_image, format="png")
    bar_chart_img = Image(bar_chart_image, width=400, height=300)
    content.append(bar_chart_img)
    content.append(Spacer(1, 12))

    # Add pie chart
    pie_chart_image = BytesIO()
    pie_chart_fig.savefig(pie_chart_image, format="png")
    pie_chart_img = Image(pie_chart_image, width=400, height=300)
    content.append(pie_chart_img)
    content.append(Spacer(1, 12))

    # Create Table object
    table_data = [["Category", "Amount"]]
    for _, row in expense_df.iterrows():
        table_data.append([row["Category"], f"${row['Amount']:.2f}"])
    table = Table(table_data)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), "grey"),
        ("TEXTCOLOR", (0, 0), (-1, 0), (1, 1, 1)),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        ("BACKGROUND", (0, 1), (-1, -1), (0.95, 0.95, 0.95)),
        ("GRID", (0, 0), (-1, -1), 1, (0.75, 0.75, 0.75)),
    ]))
    content.append(table)

    # Build PDF content
    doc.build(content)

    # Save PDF
    pdf_data = buffer.getvalue()
    with open("finance_report.pdf", "wb") as f:
        f.write(pdf_data)

def get_download_link(file_path, link_text):
    with open(file_path, "rb") as f:
        pdf_data = f.read()
    b64_pdf = base64.b64encode(pdf_data).decode("utf-8")
    return f'<a href="data:application/pdf;base64,{b64_pdf}" download="{file_path}" target="_blank">{link_text}</a>'

def main():
    st.title("Personal Finance Manager")

    # Input for Income
    st.header("Income")
    income = st.number_input("Enter your income:", value=0.0, step=1.0, key="income")

    if income < 0:
        st.warning("Income cannot be negative.")
        return

    # Initialize or load the expense DataFrame
    if 'expense_df' not in st.session_state:
        st.session_state.expense_df = pd.DataFrame(columns=["Category", "Amount"])

    # Input for Expenses
    st.header("Expenses")
    expense_category = st.text_input("Enter expense category:", key="expense_category")
    expense_amount = st.number_input("Enter expense amount:", value=0.0, step=1.0, key="expense_amount")
    add_expense = st.button("Add Expense", key="add_expense")

    total_expenses = st.session_state.expense_df["Amount"].sum()
    total_balance = income - total_expenses

    # Add expense to the DataFrame if the button is clicked and validate against negative values and balance
    if add_expense:
        if expense_amount < 0:
            st.warning("Expense amount cannot be negative.")
        elif expense_amount > total_balance:
            st.warning("Expense amount cannot be greater than total balance.")
        else:
            new_expense = pd.DataFrame({"Category": [expense_category], "Amount": [expense_amount]})
            st.session_state.expense_df = pd.concat([st.session_state.expense_df, new_expense], ignore_index=True)

    st.subheader("Manage Expenses")

    # Select operation (Update/Delete)
    selected_operation = st.selectbox("Select operation:", ["Select the operation","Update", "Delete"])

    if selected_operation == "Update":
      # Select a row to update
      selected_row = st.selectbox("Select a row to update:", st.session_state.expense_df["Category"], key="update_selected_row")
      new_amount = st.number_input("Enter updated amount:", value=0.0, step=1.0)
    
      old_amount = st.session_state.expense_df.loc[
          st.session_state.expense_df["Category"] == selected_row, "Amount"].values[0]
    
      # Calculate the maximum allowable change in the expense amount
      max_change = total_balance + old_amount
    
      update_button = st.button("Update", key="update_button")
    
      if update_button:
          if new_amount < 0:
              st.warning("Expense amount cannot be negative.")
          elif new_amount > max_change:
              st.warning("Updated amount cannot exceed the remaining balance after considering the old amount.")
          else:
              st.session_state.expense_df.loc[st.session_state.expense_df["Category"] == selected_row, "Amount"] = new_amount
              total_expenses = st.session_state.expense_df["Amount"].sum()
              total_balance = income - total_expenses


    elif selected_operation == "Delete":
        # Select a row to delete
        selected_row = st.selectbox("Select a row to delete:", st.session_state.expense_df["Category"], key="delete_selected_row")
        delete_button = st.button("Delete", key="delete_button")
        if delete_button:
            st.session_state.expense_df = st.session_state.expense_df[st.session_state.expense_df["Category"] != selected_row]

    total_expenses = st.session_state.expense_df["Amount"].sum()
    total_balance = income - total_expenses

    # Create dashboard layout with columns
    col1, col2, col3 = st.columns(3)

    with col1:
        # Display Expense Log
        st.header("Expense Log")
        if not st.session_state.expense_df.empty:
            st.text(st.session_state.expense_df.to_string(index=False))

    with col2:
        # Visualization: Expense Categories - Bar Chart
        st.header("Expense Categories")
        if not st.session_state.expense_df.empty:
            fig, ax = plt.subplots(figsize=(8, 6))
            sns.barplot(x="Amount", y="Category", data=st.session_state.expense_df, ax=ax)
            plt.xticks(rotation=45)
            st.pyplot(fig)

    with col3:
        # Visualization: Expense Categories - Pie Chart
        st.header("Expenses Breakdown")
        if not st.session_state.expense_df.empty:
            category_amounts = st.session_state.expense_df.groupby("Category")["Amount"].sum()
            fig, ax = plt.subplots()
            ax.pie(category_amounts, labels=category_amounts.index, autopct="%1.1f%%", startangle=90)
            ax.axis("equal")  # Equal aspect ratio ensures that pie is drawn as a circle.
            st.pyplot(fig)

    # Display Total Balance section
    st.header("Total Balance")
    st.write(f"Total Income: ${income}")
    st.write(f"Total Expenses: ${total_expenses:.2f}")
    st.write(f"Total Balance: ${total_balance:.2f}")
    
    colm1, colm2= st.columns(2)
    with colm1:
      explain_expenses = st.button("Explain Expenses", key="Explain_Expenses")
      if explain_expenses:
          text_to_speech = "Here are your expenses:\n"
          for _, row in st.session_state.expense_df.iterrows():
            text_to_speech += f"For {row['Category']}, you spent ${row['Amount']:.2f}\n"
          text_to_speech += f"Your total expenses are ${total_expenses:.2f}"
          tts = gTTS(text_to_speech)
          tts.save("expenses.mp3")

          st.audio("expenses.mp3")
    with colm2:
      if st.button("Generate PDF Report") and not st.session_state.expense_df.empty:
            bar_chart_fig, pie_chart_fig = generate_visualizations(st.session_state.expense_df)
            create_pdf_report(st.session_state.expense_df, income, total_expenses, total_balance, bar_chart_fig, pie_chart_fig)
            st.success("PDF Report generated successfully!")
            st.markdown(get_download_link("finance_report.pdf", "Download PDF Report"), unsafe_allow_html=True)

if __name__ == "__main__":
    main()
