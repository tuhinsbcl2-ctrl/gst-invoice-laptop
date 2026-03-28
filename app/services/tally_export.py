"""
Tally XML export for accountants.
Generates a basic Tally-compatible XML voucher export.
"""
import xml.etree.ElementTree as ET
from xml.dom import minidom


def export_to_tally_xml(invoices):
    """Export invoices to Tally XML format."""
    envelope = ET.Element('ENVELOPE')
    header = ET.SubElement(envelope, 'HEADER')
    ET.SubElement(header, 'TALLYREQUEST').text = 'Import Data'

    body = ET.SubElement(envelope, 'BODY')
    import_data = ET.SubElement(body, 'IMPORTDATA')
    request_desc = ET.SubElement(import_data, 'REQUESTDESC')
    ET.SubElement(request_desc, 'REPORTNAME').text = 'Vouchers'
    request_body = ET.SubElement(import_data, 'REQUESTDATA')

    for inv in invoices:
        tallymsg = ET.SubElement(request_body, 'TALLYMESSAGE')
        tallymsg.set('xmlns:UDF', 'TallyUDF')
        voucher = ET.SubElement(tallymsg, 'VOUCHER')
        voucher.set('VCHTYPE', 'Sales')
        voucher.set('ACTION', 'Create')

        ET.SubElement(voucher, 'DATE').text = inv.date.strftime('%Y%m%d') if inv.date else ''
        ET.SubElement(voucher, 'VOUCHERTYPENAME').text = 'Sales'
        ET.SubElement(voucher, 'VOUCHERNUMBER').text = inv.invoice_no or ''
        ET.SubElement(voucher, 'PARTYLEDGERNAME').text = inv.buyer_name or ''

        # Debit - Buyer
        allledger = ET.SubElement(voucher, 'ALLLEDGERENTRIES.LIST')
        ET.SubElement(allledger, 'LEDGERNAME').text = inv.buyer_name or ''
        ET.SubElement(allledger, 'ISDEEMEDPOSITIVE').text = 'Yes'
        ET.SubElement(allledger, 'AMOUNT').text = f'-{inv.grand_total:.2f}'

        # Credit - Sales
        sales_ledger = ET.SubElement(voucher, 'ALLLEDGERENTRIES.LIST')
        ET.SubElement(sales_ledger, 'LEDGERNAME').text = 'Sales'
        ET.SubElement(sales_ledger, 'ISDEEMEDPOSITIVE').text = 'No'
        ET.SubElement(sales_ledger, 'AMOUNT').text = f'{inv.subtotal:.2f}'

        if inv.cgst_total:
            cgst_ledger = ET.SubElement(voucher, 'ALLLEDGERENTRIES.LIST')
            ET.SubElement(cgst_ledger, 'LEDGERNAME').text = 'Output CGST'
            ET.SubElement(cgst_ledger, 'ISDEEMEDPOSITIVE').text = 'No'
            ET.SubElement(cgst_ledger, 'AMOUNT').text = f'{inv.cgst_total:.2f}'

        if inv.sgst_total:
            sgst_ledger = ET.SubElement(voucher, 'ALLLEDGERENTRIES.LIST')
            ET.SubElement(sgst_ledger, 'LEDGERNAME').text = 'Output SGST'
            ET.SubElement(sgst_ledger, 'ISDEEMEDPOSITIVE').text = 'No'
            ET.SubElement(sgst_ledger, 'AMOUNT').text = f'{inv.sgst_total:.2f}'

        if inv.igst_total:
            igst_ledger = ET.SubElement(voucher, 'ALLLEDGERENTRIES.LIST')
            ET.SubElement(igst_ledger, 'LEDGERNAME').text = 'Output IGST'
            ET.SubElement(igst_ledger, 'ISDEEMEDPOSITIVE').text = 'No'
            ET.SubElement(igst_ledger, 'AMOUNT').text = f'{inv.igst_total:.2f}'

    xml_str = minidom.parseString(ET.tostring(envelope, encoding='unicode')).toprettyxml(indent='  ')
    return xml_str.encode('utf-8')
