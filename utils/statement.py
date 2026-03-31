
from reportlab.platypus import SimpleDocTemplate,Table
from reportlab.lib.pagesizes import A4

def export_statement(file,rows):
    doc=SimpleDocTemplate(file,pagesize=A4)
    data=[["Date","Debit","Credit","Balance"]]
    for r in rows:
        data.append(r)
    table=Table(data)
    doc.build([table])
