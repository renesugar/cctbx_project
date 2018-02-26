from __future__ import absolute_import, division, print_function

import docutils.parsers.rst

def setup(app):
  app.add_directive('pubmed', PubMedDirective)

class PubMedDirective(docutils.parsers.rst.Directive):

  # this disables content in the directive
  has_content = False
  required_arguments = 1
  optional_arguments = 1
  final_argument_whitespace = True
  option_spec = {'reprint-url': docutils.parsers.rst.directives.unicode_code}

  def run(self):
    PMID = self.arguments[0]
    reprint_url = self.options.get('reprint-url', None)

    from Bio import Entrez
    Entrez.email = 'cctbxbb@phenix-online.org'
    handle = Entrez.efetch(db="pubmed", id=PMID, retmode="xml")
    XML = Entrez.read(handle)['PubmedArticle']

    def raw_html_link_new_tab(identifier, link_text, link):
      return '.. |%s| raw:: html\n\n' %identifier + \
        '   <a class="reference external" href="%s" target="_blank">%s</a>' %(
          link, link_text)

    raw_directives = []
    text = []

    for i in xrange(len(XML)):
      # Title/doi link:
      possible_doi = [ idx for idx in XML[i]["PubmedData"]["ArticleIdList"]
                       if idx.attributes["IdType"]=="doi" ]
      article = XML[i]["MedlineCitation"]["Article"]
      # Remove trailing dot and all control characters, including newline chars, from title.
      get_title = ''.join(c for c in article['ArticleTitle'].rstrip('.') if ord(c) >= 32)

      doi_link_text = None
      if len(possible_doi) > 0:
        text.append('| |%s|' %possible_doi[0])
        raw_directives.append(raw_html_link_new_tab(
          possible_doi[0], get_title, "http://dx.doi.org/%s" %possible_doi[0]))

      # Author list
      authors = [ " ".join([elem["LastName"],elem["Initials"]])
                  for elem in article["AuthorList"] ]
      text.append("| %s." %(", ".join(authors)))

      # Journal reference
      journal = article["Journal"]
      journal_text = "| *%s*" %(journal["ISOAbbreviation"])
      issue = journal["JournalIssue"]
      if 'Volume' in issue:
        journal_text += " **%s**" % issue['Volume']
        if 'Pagination' in article:
          journal_text += ", %s" % article["Pagination"]["MedlinePgn"]
      date = issue["PubDate"]
      if 'Month' in date:
        journal_text += " (%s %s %s)."%(date.get("Day",1), date["Month"], date["Year"])
      else:
        journal_text += " (%s)"%(date["Year"])
      journal_text += " [PMID:%s]"%PMID
      possible_pmc = [ idx for idx in XML[i]["PubmedData"]["ArticleIdList"]
                       if idx.attributes["IdType"]=="pmc" ]
      if len(possible_pmc) > 0:
        journal_text += " [PMC reprint: |%s|]" %possible_pmc[0]
        raw_directives.append(raw_html_link_new_tab(
          possible_pmc[0], "%s" %possible_pmc[0],
          "http://ncbi.nlm.nih.gov/pmc/articles/%s/" %possible_pmc[0]))

      if reprint_url is not None:
        journal_text += " |%s_reprint|" %PMID
        raw_directives.append(raw_html_link_new_tab(
          "%s_reprint" %PMID, "(Reprint)", reprint_url))
      text.append(journal_text)
      for directive in raw_directives:
        text.append("\n%s\n" %directive)

#   try:
#     print("vvv")
#     print("\n".join(text))
#     print("^^^")
#   except Exception:
#     pass

    # insert rst
    source = self.state_machine.input_lines.source(
      self.lineno - self.state_machine.input_offset - 1)
    lines = docutils.statemachine.string2lines(
      "\n".join(text), self.state.document.settings.tab_width, convert_whitespace=True)
    self.state_machine.insert_input(lines, source)
    return []
