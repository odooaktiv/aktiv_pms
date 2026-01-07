# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import base64
import csv
import io
import xlrd
from datetime import datetime


class PublicHoliday(models.Model):
    _name = 'public.holiday'
    _description = 'Public Holiday List'

    name = fields.Char(string="Name", required=True)
    year = fields.Char(string="Year", required=True)
    holiday_file = fields.Binary(string="Upload Holiday File (CSV/XLSX)")
    holiday_filename = fields.Char(string="Filename")
    line_ids = fields.One2many('public.holiday.line', 'list_id', string="Holiday Lines")

    @api.constrains('name', 'year')
    def _check_unique_name_year(self):
        for record in self:
            existing = self.search([
                ('name', '=', record.name),
                ('year', '=', record.year),
                ('id', '!=', record.id)
            ], limit=1)
            if existing:
                raise ValidationError("A holiday list with the same name and year already exists.")

    @api.onchange('holiday_file')
    def _onchange_holiday_file(self):
        holiday_filename = ''
        if self.holiday_file:
            self._parse_holiday_file()

    def _parse_holiday_file(self):
        """ Add lines based on value in excel """
        lines = []

        file_data = base64.b64decode(self.holiday_file)

        try:
            file_io = io.StringIO(file_data.decode("utf-8"))
            reader = csv.reader(file_io)
            next(reader, None)  # Skip header
            for row in reader:
                if len(row) >= 2:
                    try:
                        date = datetime.strptime(row[0].strip(), '%m-%d-%Y').date()
                        name = row[1].strip()
                        lines.append((0, 0, {'date': date, 'name': name}))
                    except ValueError:
                        raise ValidationError(
                            f"Invalid date format in CSV row {row}: '{row[0]}'. "
                            f"Expected format: MM-DD-YYYY"
                        )
                    except Exception as e:
                        raise ValidationError(f"Error in CSV row: {row}. {str(e)}")
        except UnicodeDecodeError:
            # Try Excel if CSV fails
            try:
                book = xlrd.open_workbook(file_contents=file_data)
                sheet = book.sheet_by_index(0)
                for rx in range(1, sheet.nrows):  # Skip header
                    try:
                        date_val = sheet.cell_value(rx, 0)
                        if isinstance(date_val, float):  # Excel date
                            date = datetime(*xlrd.xldate_as_tuple(date_val, book.datemode)).date()
                        else:
                            date = datetime.strptime(date_val.strip(), '%m-%d-%Y').date()
                        name = str(sheet.cell_value(rx, 1)).strip()
                        lines.append((0, 0, {'date': date, 'name': name}))
                    except ValueError:
                        raise ValidationError(
                            f"Invalid date format in Excel row {rx + 1}: '{date_val}'. Expected format: MM-DD-YYYY"
                        )
                    except Exception as e:
                        raise ValidationError(f"Error in Excel row {rx + 1}: {str(e)}")
            except Exception:
                raise ValidationError("Unable to read the uploaded file. Please upload a valid CSV or Excel file.")
        self.write({'line_ids': lines})
