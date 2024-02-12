import os
import jinja2
#from md2tex import LaTeXMarkdown
import mistletoe
from mistletoe.latex_renderer import LaTeXRenderer
from patterns import PatternSubstitutions

class LaTeXPatternSubstitutions(PatternSubstitutions):
	def __init__(self):
		PatternSubstitutions.__init__(self, [
			 ['"', self.double_quote],
			 ['_', '\_'],
			 ['%', '\%'],
			 ['/eol/', '\\\\\\\\'],
			 ['/eop/', '\n\n'],
			 ['/vsp/', '\\\\vspace*{6pt}'],
			 ['/center/', self.centerline],
			 ['/pagebreak/', '\\\\pagebreak'],
			 ['\\\\verb', ''], #verbatim mode not compatible with multicolumn
			 ['\|', ''] #verbatim mode not compatible with multicolumn
		])
		self.dquote =  1
		self.cline = -1

	def double_quote(self, matchobj):
		self.dquote = (self.dquote + 1) % 2
		return ["``", "''"][self.dquote]

	def centerline(self, matchobj):
		self.cline = (self.cline + 1) % 2
		return ['\\begin{nscenter}','\\end{nscenter}'][self.cline]

class DoubleQuoteFix(PatternSubstitutions):
	def __init__(self):
		PatternSubstitutions.__init__(self, [
			 ['"', self.double_quote],
		])
		self.dquote =  1

	def double_quote(self, matchobj):
		self.dquote = (self.dquote + 1) % 2
		return ["``", "''"][self.dquote]

class MyLaTeX(LaTeXRenderer):
	def __init__(self):
		super().__init__()
		self.depth = 0
		self.deep_pass = None

	def render_table(self, token):
		rv = super().render_table(token)
		return '\n\n{}\n\n'.format(rv)
		
	def render_document(self, token):
		template = ('{inner}')
		self.footnotes.update(token.footnotes)
		return template.format(inner=self.render_inner(token),
		                       packages=self.render_packages())

	def render_quote(self, token):
		self.depth += 1
		if self.depth > 1:
			template = '\\begin{{fixedsidebar}}\n{inner}\\end{{fixedsidebar}}\n'
			rv = template.format(inner=self.render_inner(token))
			self.deep_pass = rv
			return rv

		template = '\\begin{{boxtext}}\n{inner}\\end{{boxtext}}\n'
		rv = template.format(inner=self.render_inner(token))
		if self.deep_pass:
			rv = self.deep_pass
		self.depth -= 1
		self.deep_pass = False
		return rv
		
	def render_block_code(self, token):
		inner = self.render_raw_text(token.children[0], False)
		return inner

class MemLoader(jinja2.BaseLoader):
    def get_source(self, environment, template):
    	if not template:
    		template = ''
    	return template, None, lambda: False

class TemplateEngine:
	'''Simple helper for jinja2 templates. Looks for templates in X.template.extension" 
	files, where .extension is usually set by the subclass. Impleases the |usetemplate
	filter, allowing for a template to call another template.'''
	def use_template(self, obj, template):
		'''example: X | usetemplate('foo')
		Instaniates template foo with objected X'''
		return self.Render(obj,template)

	def as_set(self, obj):
		return set(obj)

	def inplace(self, obj, text):
		'''example: X | inplace(template_text)'''
		try:
			template = self.mem_env.get_template(text)
		except jinja2.TemplateSyntaxError as err:
			raise RuntimeError('Invalid template:\n{}'.format(text))
		return template.render(obj)

	def cap_all_words(self,obj):
		words = obj.split(' ')
		caps = []
		for w in words:

			if w in ['of', 'the', 'a']:
				fixed = w
			else:
				fixed = w.capitalize()
			caps.append(fixed)
		return ' '.join(caps)

	def has_intersect(self, obj, prm):
		s1 = set(prm)
		s2 = set(obj)
		un = s1 & s2
		return len(un) > 0

	def chunk_list(self, lst, *args):
		rv = []
		cnt = 0
		nxt = []
		szp = 0
		for i in lst:
			nxt.append(i)
			cnt += 1
			if cnt == args[szp]:
				cnt = 0
				rv.append(nxt)
				nxt = []
				szp += 1
				if szp >= len(args):
					szp = len(args) - 1
		rv.append(nxt)
		return rv

	def __init__(self, ext, path):
		self.path = path
		self.extension = ext
		self.template_env = jinja2.Environment(loader=jinja2.FileSystemLoader(path), extensions=['jinja2.ext.loopcontrols'])
		self.template_env.filters['usetemplate'] = self.use_template
		self.template_env.filters['as_set'] = self.as_set
		self.template_env.filters['capitalize'] = self.cap_all_words
		self.template_env.filters['inplace'] = self.inplace
		self.template_env.filters['chunk'] = self.chunk_list
		self.template_env.filters['has_intersect'] = self.has_intersect
		self.mem_env = jinja2.Environment(loader=MemLoader())
			
	def Render(self, obj, template):
		tname = "%s.template.%s" % (template, self.extension)
		try:
			template = self.template_env.get_template(tname)
		except jinja2.UndefinedError as err:
			raise Exception('Template \"{0}\" not found at path {2}'.format(
				tname, self.extention, self.path)) from None
		except jinja2.TemplateSyntaxError as err:
			line1 = 'Syntax error in on line {0} of template \"{1}\" at path {2}.'.format(
				err.lineno,tname, self.path)
			raise Exception(line1 + '\n\t' + err.message) from None
		retval = template.render(obj)
		return retval
	
class HTMLTemplateEngine(TemplateEngine):
	def __init__(self, path='.'):
		TemplateEngine.__init__(self, 'html', path)

class TextTemplateEngine(TemplateEngine):
    def __init__(self, path='.'):
        TemplateEngine.__init__(self, 'txt', path)
        self.template_env.trim_blocks = True
        self.template_env.lstrip_blocks = True   

class LaTeXTemplateEngine(TemplateEngine):

	def make_hfit(self, line, mx):
		if len(line) > mx:
			return '{\\small %s}' % line
		else:
			return line

	#escape non-markdown sequences
	def escape(self, txt):
		txt = txt.replace('$', '\\$')
		txt = txt.replace('%', '\\%')
		txt = txt.replace('&', '\\&')
		txt = txt.replace('_', '\_')
		txt = txt.replace('%', '\%')
		txt = txt.replace('`','')
		return txt

	def extra_markdown(self,txt):
		return self.LPS.process(txt)

	def markdown(self, txt):
		#txt = self.escape(txt)
		txt = mistletoe.markdown(txt, MyLaTeX)
		txt = self.extra_markdown(txt)
		if txt:
			if (txt[0] == '\n'): txt = txt[1:]
		return txt
		#return LaTeXMarkdown(self.escape(txt))
		
	def Render(self, obj, template):
		pass1 = super().Render(obj,template)
		return self.DQF.process(pass1)

	def __init__(self, path='.'):
		TemplateEngine.__init__(self, 'tex', path)
		self.template_env.block_start_string = '/$'
		self.template_env.block_end_string = '$/'
		self.template_env.variable_start_string = '/@'
		self.template_env.variable_end_string = '@/'
		self.template_env.trim_blocks = True
		self.template_env.lstrip_blocks = True
		self.template_env.filters['make_hfit'] = self.make_hfit
		self.template_env.filters['escape'] = self.escape
		self.template_env.filters['markdown'] = self.markdown
		self.template_env.comment_start_string = '/##'
		self.template_env.comment_start_string = '##/'
		self.LPS = LaTeXPatternSubstitutions()
		self.DQF = DoubleQuoteFix()

