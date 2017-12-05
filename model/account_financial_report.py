# -*- encoding: utf-8 -*-
###########################################################################
#    Module Writen to OpenERP, Open Source Management Solution
#    Copyright (C) OpenERP Venezuela (<http://openerp.com.ve>).
#    All Rights Reserved
# Credits######################################################
#    Coded by:   Humberto Arocha humberto@openerp.com.ve
#                Angelica Barrios angelicaisabelb@gmail.com
#               Jordi Esteve <jesteve@zikzakmedia.com>
#               Javier Duran <javieredm@gmail.com>
#    Planified by: Humberto Arocha
#    Finance by: LUBCAN COL S.A.S http://www.lubcancol.com
#    Audited by: Humberto Arocha humberto@openerp.com.ve
#############################################################################
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
##############################################################################
from openerp import models, fields, api
# from osv import osv, fields
from openerp.osv import fields, osv

# import pooler
from openerp import pooler

import time
# from tools.translate import _
from openerp.tools.translate import _

class account_financial_report(osv.osv):
	_name = "afr"

	_columns = {
		'name': fields.char('Name', size=128, required=True),
		'company_id': fields.many2one('res.company', 'Company', required=True),
		'currency_id': fields.many2one(
			'res.currency', 'Currency', help="Currency at which this report will be expressed. If not selected will be used the one set in the company"),
		'inf_type': fields.selection(
			[('BS', 'Balance Sheet'), ('IS', 'Income Statement')], 'Type', required=True),
		'columns': fields.selection([('one', 'End. Balance'), ('two', 'Debit | Credit'), ('four', 'Initial | Debit | Credit | YTD'),
									('five', 'Initial | Debit | Credit | Period | YTD'), ('qtr', "4 QTR's | YTD"), ('thirteen', '12 Months | YTD')], 'Columns', required=True),
		'display_account': fields.selection([('all', 'All Accounts'), ('bal', 'With Balance'),
											('mov', 'With movements'), ('bal_mov', 'With Balance / Movements')], 'Display accounts'),
		'display_account_level': fields.integer(
			'Up to level', help='Display accounts up to this level (0 to show all)'),
		'account_ids': fields.many2many(
			'account.account', 'afr_account_rel', 'afr_id', 'account_id', 'Root accounts', required=True),
		'fiscalyear_id': fields.many2one(
			'account.fiscalyear', 'Fiscal year', help='Fiscal Year for this report', required=True),
		'period_ids': fields.many2many('account.period', 'afr_period_rel', 'afr_id',
									   'period_id', 'Periods', help='All periods in the fiscal year if empty'),

		'analytic_ledger': fields.boolean(
			'Analytic Ledger', help="Allows to Generate an Analytic Ledger for accounts with moves. Available when Balance Sheet and 'Initial | Debit | Credit | YTD' are selected"),
		'journal_ledger': fields.boolean(
			'journal Ledger', help="Allows to Generate an journal Ledger for accounts with moves. Available when Balance Sheet and 'Initial | Debit | Credit | YTD' are selected"),
		'partner_balance': fields.boolean('Partner Balance', help="Allows to "
										  "Generate a Partner Balance for accounts with moves. Available when "
										  "Balance Sheet and 'Initial | Debit | Credit | YTD' are selected"),
		'tot_check': fields.boolean(
			'Summarize?', help='Checking will add a new line at the end of the Report which will Summarize Columns in Report'),
		'lab_str':
		fields.char(
			'Description',
			help='Description for the Summary',
			size=128),
		'target_move': fields.selection([('posted', 'All Posted Entries'),
										('all', 'All Entries'),
										 ], 'Entries to Include', required=True,
										help='Print All Accounting Entries or just Posted Accounting Entries'),

		#~ Deprecated fields
		'filter': fields.selection([('bydate', 'By Date'), ('byperiod', 'By Period'),
								   ('all', 'By Date and Period'), ('none', 'No Filter')], 'Date/Period Filter'),
		'date_to': fields.date('End date'),
		'date_from': fields.date('Start date'),
	}

	_defaults = {
		'display_account_level': lambda *a: 0,
		'inf_type': lambda *a: 'BS',
		'company_id': lambda self, cr, uid, c:
		self.pool.get(
			'res.company')._company_default_get(
			cr,
			uid,
			'account.invoice',
			context=c),
		'fiscalyear_id': lambda self, cr, uid, c:
		self.pool.get('account.fiscalyear').find(cr, uid),
		'display_account': lambda *a: 'bal_mov',
		'columns': lambda *a: 'five',

		'date_from': lambda *a: time.strftime('%Y-%m-%d'),
		'date_to': lambda *a: time.strftime('%Y-%m-%d'),
		'filter': lambda *a: 'byperiod',
		'target_move': 'posted',
	}

	def copy(self, cr, uid, id, defaults, context=None):
		if context is None:
			context = {}
		previous_name = self.browse(cr, uid, id, context=context).name
		new_name = _('Copy of %s') % previous_name
		lst = self.search(cr, uid, [(
			'name', 'like', new_name)], context=context)
		if lst:
			new_name = '%s (%s)' % (new_name, len(lst) + 1)
		defaults['name'] = new_name
		return (
			super(
				account_financial_report,
				self).copy(
				cr,
				uid,
				id,
				defaults,
				context=context)
		)

	@api.onchange('inf_type')
	def onchange_inf_type(self):
		if self.inf_type != 'BS':
			self.analytic_ledger= False
			

	@api.onchange('columns', 'fiscalyear_id', 'period_ids')
	def onchange_columns(self):

		if self.columns != 'four':
			self.analytic_ledger = False

		if self.columns in ('qtr', 'thirteen'):
			p_obj = self.env["account.period"]
			period_ids = p_obj.search([('fiscalyear_id', '=', self.fiscalyear_id.id), ('special', '=', False)])
			self.period_ids= period_ids
		else:
			self.period_ids= []
		
	@api.onchange('company_id', 'analytic_ledger')
	def onchange_analytic_ledger(self):
		self= self.with_context(company_id=self.company_id.id)
		cur_id = self.env['res.company'].browse(self.company_id).currency_id.id
		self.currency_id= cur_id

	@api.onchange('company_id')
	def onchange_company_id(self):

		self= self.with_context(company_id=self.company_id.id)
		cur_id = self.env['res.company'].browse(self.company_id).currency_id.id
		fy_id = self.env['account.fiscalyear'].find()
		self.fiscalyear_id=fy_id
		self.currency_id= cur_id
		self.account_ids=[]
		self.period_ids=[]

account_financial_report()

