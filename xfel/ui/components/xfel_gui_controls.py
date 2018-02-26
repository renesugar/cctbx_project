from __future__ import division

'''
Author      : Lyubimov, A.Y.
Created     : 06/03/2016
Last Changed: 06/03/2016
Description : XFEL UI Custom Widgets and Controls
'''

import os
import wx
import wx.lib.agw.floatspin as fs
from wxtbx import metallicbutton as mb

# Platform-specific stuff
# TODO: Will need to test this on Windows at some point
if wx.Platform == '__WXGTK__':
  norm_font_size = 10
  button_font_size = 12
  LABEL_SIZE = 14
  CAPTION_SIZE = 12
elif wx.Platform == '__WXMAC__':
  norm_font_size = 12
  button_font_size = 14
  LABEL_SIZE = 14
  CAPTION_SIZE = 12
elif (wx.Platform == '__WXMSW__'):
  norm_font_size = 9
  button_font_size = 11
  LABEL_SIZE = 11
  CAPTION_SIZE = 9

icons = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icons/')

# --------------------------------- Buttons ---------------------------------- #

class GradButton(mb.MetallicButton):
  def __init__(self, parent, label='', bmp=None, size=wx.DefaultSize,
               style=mb.MB_STYLE_BOLD_LABEL, handler_function=None,
               user_data=None, start_color=(218, 218, 218),
               gradient_percent=0, highlight_color=(230, 230, 230),
               label_size=LABEL_SIZE, caption_size=CAPTION_SIZE,
               button_margin=4, disable_after_click=0) :
    if isinstance(bmp, str) :
      bmp = self.StandardBitmap(bmp)
      bmp_size = bmp.GetSize()
      if bmp_size > size[1]:
        size = (size[0], 1.5 * bmp_size[1])
    mb.MetallicButton.__init__(self,
                               parent=parent,
                               label=label,
                               bmp=bmp,
                               size=size,
                               style=style,
                               name=str(user_data),
                               start_color=start_color,
                               gradient_percent=gradient_percent,
                               highlight_color=highlight_color,
                               label_size=label_size,
                               caption_size=caption_size,
                               button_margin=button_margin,
                               disable_after_click=disable_after_click
                               )
    if handler_function is not None:
     self.bind_event(wx.EVT_BUTTON, handler_function)

  def StandardBitmap(img_name, size=None):
    img_path = img_name
    img = wx.Image(img_path, type=wx.BITMAP_TYPE_ANY, index=-1)
    if size is not None:
     (w, h) = size
     img.Rescale(w, h)
    bmp = img.ConvertToBitmap()
    return bmp

class RunBlockButton(GradButton):
  def __init__(self, parent, block, size=wx.DefaultSize):
    self.block = block
    db = block.app
    self.first_run = db.get_run(run_number=block.startrun).run
    self.rnum = block.rungroup_id
    if block.endrun is None:
      self.last_run = None
    else:
      self.last_run = db.get_run(run_number=block.endrun).run

    GradButton.__init__(self, parent=parent, label='',
                        size=size)
    self.update_label()

  def update_label(self):
    first = self.first_run
    if self.last_run is None:
      last = ' ...'
    else:
      last = ' - {}'.format(self.last_run)

    self.block_label = '[{}] runs {}{}'.format(self.rnum, first, last)
    self.SetLabel(self.block_label)
    self.Refresh()

class TagButton(GradButton):
  def __init__(self, parent, run, size=wx.DefaultSize):
    self.run = run
    self.tags = self.run.tags
    self.parent = parent

    GradButton.__init__(self, parent=parent, size=size)

    self.update_label()

  def update_label(self):

    label = ', '.join([i.name for i in self.tags])
    self.SetLabel(label)
    self.SetFont(wx.Font(button_font_size, wx.DEFAULT, wx.NORMAL, wx.NORMAL))
    self.Refresh()

  def change_tags(self):
    ''' Calls dialog with tag options for all runs; user will select tags
        for this specific run
    '''
    all_tags = self.run.app.get_all_tags()
    all_tag_names = [t.name for t in all_tags]
    tag_dlg = wx.MultiChoiceDialog(self,
                                   message='Available sample tags',
                                   caption='Sample Tags',
                                   choices=all_tag_names)
    # Get indices of selected items (if any) and set them to checked
    local_tag_names = [i.name for i in self.tags]
    indices = [all_tag_names.index(i) for i in all_tag_names if i in local_tag_names]
    tag_dlg.SetSelections(indices)
    tag_dlg.Fit()

    if (tag_dlg.ShowModal() == wx.ID_OK):
      tag_indices = tag_dlg.GetSelections()

      self.tags = [i for i in all_tags if all_tags.index(i) in
                   tag_indices]
      old_tags = self.run.tags
      old_tag_names = [t.name for t in old_tags]
      new_tag_names = [t.name for t in self.tags]

      for new_tag in self.tags:
        if new_tag.name not in old_tag_names:
          self.run.add_tag(new_tag)

      for old_tag in old_tags:
        if old_tag.name not in new_tag_names:
          self.run.remove_tag(old_tag)

      # re-synchronize, just in case
      self.tags = self.run.tags

      self.update_label()


# --------------------------------- Controls --------------------------------- #

class CtrlBase(wx.Panel):
  ''' Control panel base class '''
  def __init__(self,
               parent,
               label_style='normal',
               content_style='normal',
               size=wx.DefaultSize):

    wx.Panel.__init__(self, parent=parent, id=wx.ID_ANY, size=size)
    if label_style == 'normal':
      self.font = wx.Font(norm_font_size, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
    elif label_style == 'bold':
      self.font = wx.Font(norm_font_size, wx.DEFAULT, wx.NORMAL, wx.BOLD)
    elif label_style == 'italic':
      self.font = wx.Font(norm_font_size, wx.DEFAULT, wx.ITALIC, wx.NORMAL)
    elif label_style == 'italic_bold':
      self.font = wx.Font(norm_font_size, wx.DEFAULT, wx.ITALIC, wx.BOLD)

    if content_style == 'normal':
      self.cfont = wx.Font(norm_font_size, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
    elif content_style == 'bold':
      self.cfont = wx.Font(norm_font_size, wx.DEFAULT, wx.NORMAL, wx.BOLD)
    elif content_style == 'italic':
      self.cfont = wx.Font(norm_font_size, wx.DEFAULT, wx.ITALIC, wx.NORMAL)
    elif content_style == 'italic_bold':
      self.cfont = wx.Font(norm_font_size, wx.DEFAULT, wx.ITALIC, wx.BOLD)

class InputCtrl(CtrlBase):
  ''' Generic panel that will place a text control, with a label and an
      optional Browse / magnifying-glass buttons into a window'''

  def __init__(self, parent,
               label='', label_size=(100, -1),
               label_style='normal',
               button=False, value=''):

    CtrlBase.__init__(self, parent=parent, label_style=label_style)

    output_box = wx.FlexGridSizer(1, 4, 0, 10)
    self.txt = wx.StaticText(self, label=label, size=label_size)
    self.txt.SetFont(self.font)
    output_box.Add(self.txt)

    self.ctr = wx.TextCtrl(self) #, size=ctr_size)
    self.ctr.SetValue(value)
    output_box.Add(self.ctr, flag=wx.EXPAND)

    self.btn_browse = wx.Button(self, label='Browse...')
    self.btn_mag = wx.BitmapButton(self,
                                   bitmap=wx.Bitmap('{}/16x16/viewmag.png'
                                                    ''.format(icons)))
    output_box.Add(self.btn_browse, flag=wx.RESERVE_SPACE_EVEN_IF_HIDDEN)
    output_box.Add(self.btn_mag, flag=wx.RESERVE_SPACE_EVEN_IF_HIDDEN)

    if not button:
      self.btn_browse.Hide()
      self.btn_mag.Hide()

    output_box.AddGrowableCol(1, 1)
    self.SetSizer(output_box)

class TextButtonCtrl(CtrlBase):
  ''' Generic panel that will place a text control, with a label and an
      optional large button, and an optional bitmap button'''

  def __init__(self, parent,
               label='', label_size=(100, -1),
               label_style='normal',
               text_style=wx.TE_LEFT,
               ctrl_size=(200, -1),
               big_button=False,
               big_button_label='Browse...',
               big_button_size=wx.DefaultSize,
               ghost_button=True,
               value=''):

    CtrlBase.__init__(self, parent=parent, label_style=label_style)

    output_box = wx.FlexGridSizer(1, 4, 0, 10)
    self.txt = wx.StaticText(self, label=label, size=label_size)
    self.txt.SetFont(self.font)
    output_box.Add(self.txt)

    self.ctr = wx.TextCtrl(self, style=text_style, size=ctrl_size)
    self.ctr.SetValue(value)
    output_box.Add(self.ctr, flag=wx.EXPAND)

    self.btn_big = wx.Button(self, label=big_button_label, size=big_button_size)
    if ghost_button:
      output_box.Add(self.btn_big, flag=wx.RESERVE_SPACE_EVEN_IF_HIDDEN)
    else:
      output_box.Add(self.btn_big)

    if not big_button:
      self.btn_big.Hide()

    output_box.AddGrowableCol(1, 1)
    self.SetSizer(output_box)

class TwoButtonCtrl(CtrlBase):
  ''' Generic panel that will place a text control, with a label and an
      optional large button, and an optional bitmap button'''

  def __init__(self, parent,
               label='', label_size=(100, -1),
               label_style='normal',
               text_style=wx.TE_LEFT,
               button1=False,
               button1_label='Browse...',
               button1_size=wx.DefaultSize,
               button2=False,
               button2_label='Default',
               button2_size=wx.DefaultSize,
               value=''):

    CtrlBase.__init__(self, parent=parent, label_style=label_style)

    output_box = wx.FlexGridSizer(1, 5, 0, 10)
    self.txt = wx.StaticText(self, label=label, size=label_size)
    self.txt.SetFont(self.font)
    output_box.Add(self.txt)

    self.ctr = wx.TextCtrl(self, style=text_style)
    self.ctr.SetValue(value)
    output_box.Add(self.ctr, flag=wx.EXPAND)

    if button1:
      self.button1 = wx.Button(self, label=button1_label, size=button1_size)
      output_box.Add(self.button1)

    if button2:
      self.button2 = wx.Button(self, label=button2_label, size=button2_size)
      output_box.Add(self.button2)

    output_box.AddGrowableCol(1, 1)
    self.SetSizer(output_box)

class OptionCtrl(CtrlBase):
  ''' Generic panel will place a text control w/ label '''
  def __init__(self, parent, items,
               label='',
               label_size=(100, -1),
               label_style='normal',
               sub_labels=[],
               ctrl_size=(300, -1)):

    CtrlBase.__init__(self, parent=parent, label_style=label_style)

    if label != '':
      opt_box = wx.FlexGridSizer(1, len(items) * 2 + 1, 0, 10)
      self.txt = wx.StaticText(self, label=label, size=label_size)
      self.txt.SetFont(self.font)
      opt_box.Add(self.txt, flag=wx.ALIGN_CENTER_VERTICAL)
    else:
      opt_box = wx.FlexGridSizer(1, len(items) * 2, 0, 10)

    for key, value in items:
      if sub_labels != []:
        sub_label = sub_labels[items.index((key, value))].decode('utf-8')
      else:
        sub_label = key

      if len(items) > 1:
        opt_label = wx.StaticText(self, id=wx.ID_ANY, label=sub_label)
        opt_box.Add(opt_label, flag=wx.ALIGN_CENTER_VERTICAL)

      item = wx.TextCtrl(self, id=wx.ID_ANY, size=ctrl_size,
                         style=wx.TE_PROCESS_ENTER)
      item.SetValue(str(value))
      opt_box.Add(item, flag=wx.ALIGN_CENTER_VERTICAL)
      self.__setattr__(key, item)

    self.SetSizer(opt_box)

class VerticalOptionCtrl(CtrlBase):
  ''' Generic panel will place a text control w/ label in column'''
  def __init__(self, parent, items,
               label='',
               label_size=(100, -1),
               label_style='normal',
               sub_labels=[],
               ctrl_size=(300, -1)):

    CtrlBase.__init__(self, parent=parent, label_style=label_style)

    if label != '':
      opt_box = wx.FlexGridSizer(len(items) * 2 + 1, 2, 10, 10)
      self.txt = wx.StaticText(self, label=label, size=label_size)
      self.txt.SetFont(self.font)
      opt_box.Add(self.txt, flag=wx.ALIGN_CENTER_VERTICAL)
      opt_box.Add((0, 0))
    else:
      opt_box = wx.FlexGridSizer(len(items) * 2, 2, 10, 10)

    for key, value in items:
      if sub_labels != []:
        sub_label = sub_labels[items.index((key, value))].decode('utf-8')
      else:
        sub_label = key

      if len(items) > 1:
        opt_label = wx.StaticText(self, id=wx.ID_ANY, label=sub_label)
        opt_box.Add(opt_label, flag=wx.ALIGN_CENTER_VERTICAL)

      item = wx.TextCtrl(self, id=wx.ID_ANY, size=ctrl_size,
                         style=wx.TE_PROCESS_ENTER)
      item.SetValue(str(value))
      opt_box.Add(item, flag=wx.ALIGN_CENTER_VERTICAL)
      self.__setattr__(key, item)

    self.SetSizer(opt_box)

class IntFloatSpin(fs.FloatSpin):
  def GetValue(self):
    float_value = super(IntFloatSpin, self).GetValue()
    int_value = int(round(float_value))
    return int_value

class SpinCtrl(CtrlBase):
  ''' Generic panel will place a spin control w/ label '''
  def __init__(self, parent,
               label='',
               label_size=(200, -1),
               label_style='normal',
               ctrl_size=(60, -1),
               ctrl_value='3',
               ctrl_max=10,
               ctrl_min=0,
               ctrl_step=1,
               ctrl_digits=0):

    CtrlBase.__init__(self, parent=parent, label_style=label_style)

    ctr_box = wx.FlexGridSizer(1, 3, 0, 10)
    self.txt = wx.StaticText(self, label=label.decode('utf-8'),
                             size=label_size)
    self.txt.SetFont(self.font)

    floatspin_class = IntFloatSpin if ctrl_digits == 0 else fs.FloatSpin
    self.ctr = floatspin_class(self, value=ctrl_value, max_val=(ctrl_max),
                              min_val=(ctrl_min), increment=ctrl_step,
                              digits=ctrl_digits, size=ctrl_size)
    ctr_box.Add(self.txt, flag=wx.ALIGN_CENTER_VERTICAL)
    ctr_box.Add(self.ctr, flag=wx.ALIGN_CENTER_VERTICAL)

    self.SetSizer(ctr_box)

class ChoiceCtrl(CtrlBase):
  ''' Generic panel will place a choice control w/ label '''

  def __init__(self, parent,
               choices,
               label='',
               label_size=(200, -1),
               label_style='normal',
               ctrl_size=(100, -1)):

    CtrlBase.__init__(self, parent=parent, label_style=label_style)
    ctr_box = wx.FlexGridSizer(1, 3, 0, 10)
    self.txt = wx.StaticText(self, label=label, size=label_size)
    self.txt.SetFont(self.font)

    # Check if choices are tuples, extract data and assign to items if so
    if all(isinstance(i, tuple) for i in choices):
      items = [i[0] for i in choices]
      self.ctr = wx.Choice(self, size=ctrl_size, choices=items)
      for choice in choices:
        item_idx = self.ctr.FindString(choice[0])
        self.ctr.SetClientData(item_idx, choice[1])
    else:
      self.ctr = wx.Choice(self, size=ctrl_size, choices=choices)

    ctr_box.Add(self.txt, flag=wx.ALIGN_CENTER_VERTICAL)
    ctr_box.Add(self.ctr, flag=wx.ALIGN_CENTER_VERTICAL)

    self.SetSizer(ctr_box)

class CheckListCtrl(CtrlBase):
  def __init__(self, parent,
               choices,
               label='',
               label_size=(200, -1),
               label_style='normal',
               ctrl_size=(150, -1),
               direction='horizontal'):

    CtrlBase.__init__(self, parent=parent, label_style=label_style)

    self.txt = wx.StaticText(self, label=label, size=label_size)
    self.txt.SetFont(self.font)
    self.ctr = wx.CheckListBox(self, size=ctrl_size, choices=choices)

    if label == '':
      ctr_box = wx.BoxSizer(wx.VERTICAL)
    else:
      if direction == 'horizontal':
        ctr_box = wx.FlexGridSizer(1, 2, 0, 10)
      elif direction == 'vertical':
        ctr_box = wx.FlexGridSizer(2, 1, 10, 0)
      ctr_box.Add(self.txt, flag=wx.ALIGN_CENTER_VERTICAL)

    ctr_box.Add(self.ctr, proportion=1,
                flag=wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)

    self.SetSizer(ctr_box)

class MultiChoiceCtrl(CtrlBase):
  ''' Generic panel with multiple choice controls / labels '''

  def __init__(self, parent, items,
               label='',
               label_size=(200, -1),
               label_style='normal',
               ctrl_size=(100, -1)):
    CtrlBase.__init__(self, parent=parent, label_style=label_style)


    choice_box = wx.FlexGridSizer(1, len(items) * 2 + 1, 0, 10)
    self.txt = wx.StaticText(self, label=label, size=label_size)
    self.txt.SetFont(self.font)
    choice_box.Add(self.txt, flag=wx.ALIGN_CENTER_VERTICAL)

    for key, choices in items.iteritems():
      if len(items) > 1:
        ch_label =wx.StaticText(self, id=wx.ID_ANY, label=key)
        choice_box.Add(ch_label, flag=wx.ALIGN_CENTER_VERTICAL)

      item = wx.Choice(self, id=wx.ID_ANY, size=ctrl_size, choices=choices)
      choice_box.Add(item, flag=wx.ALIGN_CENTER_VERTICAL)
      self.__setattr__(key, item)

    self.SetSizer(choice_box)

class TableCtrl(CtrlBase):
  ''' Generic panel will place a table w/ x and y labels
      Data must be a list of lists for multi-column tables '''

  def __init__(self, parent,
               clabels=[],
               clabel_size=(200, -1),
               rlabels=[],
               rlabel_size=(200, -1),
               contents=[],
               label_style='normal',
               content_style='normal'):

    CtrlBase.__init__(self, parent=parent, label_style=label_style,
                      content_style=content_style)
    nrows = len(rlabels) + 1

    if len(clabels) == 0:
      ncols = 2
    else:
      ncols = len(clabels) + 1
    self.sizer = wx.FlexGridSizer(nrows, ncols, 10, 10)

    # add column labels (xlabels)
    if len(clabels) > 0:
      self.sizer.Add(wx.StaticText(self, label=''))
      for item in column_labels:
        clabel = wx.StaticText(self, label=i.decode('utf-8'), size=clabel_size)
        clabel.SetFont(self.font)
        self.sizer.Add(clabel)

    # add row labels and row contents
    for l in rlabels:
      row_label = wx.StaticText(self, label=l.decode('utf-8'), size=rlabel_size)
      row_label.SetFont(self.font)
      self.sizer.Add(row_label)

      # Add data to table
      c_index = rlabels.index(l)
      for item in contents[c_index]:
        cell = wx.StaticText(self, label=item.decode('utf-8'))
        cell.SetFont(self.cfont)
        self.sizer.Add(cell)

    self.SetSizer(self.sizer)

class RadioCtrl(CtrlBase):
  '''Generic panel with multiple radio buttons.'''

  def __init__(self, parent,
               label='',
               label_size=(200, -1),
               label_style='normal',
               ctrl_size=(100, -1),
               direction='horizontal',
               items={}):
    CtrlBase.__init__(self, parent=parent, label_style=label_style)

    if direction == 'horizontal':
      radio_group = wx.FlexGridSizer(1, len(items) + 1, 0, 10)
    else:
      radio_group = wx.FlexGridSizer(len(items) + 1, 1, 0, 10)
    if label != '':
      self.txt = wx.StaticText(self, label=label, size=label_size)
      self.txt.SetFont(self.font)
      radio_group.Add(self.txt, flag=wx.ALIGN_CENTER_VERTICAL)

    for key, value in items.iteritems():
      button = wx.RadioButton(self, id=wx.ID_ANY, label=value)
      radio_group.Add(button)
      self.__setattr__(key, button)

    self.SetSizer(radio_group)

# Use a mixin to support sorting by columns
import wx.lib.mixins.listctrl as listmix

class SortableListCtrl(wx.ListCtrl, listmix.ColumnSorterMixin):
  def __init__(self, parent, style=wx.LC_ICON):
    self.parent = parent
    self.sortable_mixin = listmix
    wx.ListCtrl.__init__(self, parent, style=style)

  def initialize_sortable_columns(self, n_col=0, itemDataMap={}):
    self.itemDataMap = itemDataMap
    self.sortable_mixin.ColumnSorterMixin.__init__(self, n_col)
    sortable_list = self.GetListCtrl()
    if sortable_list:
      sortable_list.Bind(wx.EVT_LIST_COL_CLICK, self.__OnColClick, sortable_list)

  def __OnColClick(self, e):
    self._col = e.GetColumn()
    self._colSortFlag[self._col] = int(not self._colSortFlag[self._col])
    self.GetListCtrl().SortItems(self.GetColumnSorter())
    self.OnSortOrderChanged()
    if hasattr(self.parent, 'onColClick'):
      self.parent.onColClick(e)

  def RestoreSortOrder(self, col, colSortFlag):
    self._col = col
    self._colSortFlag = colSortFlag
    self.GetListCtrl().SortItems(self.GetColumnSorter())
    self.OnSortOrderChanged()

  def GetListCtrl(self):
    return self

# ------------------------------- UI Elements -------------------------------- #

class RunBlock(CtrlBase):
  def __init__(self, parent, block,
               label_style='normal',
               content_style='normal'):

    self.block = block

    CtrlBase.__init__(self, parent=parent, label_style=label_style,
                      content_style=content_style)

    self.sizer = wx.FlexGridSizer(1, 2, 0, 5)
    self.new_runblock = RunBlockButton(self, size=(200, -1), block=block)
    # self.del_runblock = wx.BitmapButton(self,
    #                     bitmap=wx.Bitmap('{}/16x16/delete.png'.format(icons)))

    self.sizer.Add(self.new_runblock)
    # self.sizer.Add(self.del_runblock)

    self.SetSizer(self.sizer)


class PHILBox(CtrlBase):
  def __init__(self, parent,
               btn_import=True,
               btn_import_size=(120, -1),
               btn_import_label='Import PHIL',
               btn_export=False,
               btn_export_size=(120, -1),
               btn_export_label='Export PHIL',
               btn_default=True,
               btn_default_size=(120, -1),
               btn_default_label='Default PHIL',
               ctr_size=(-1, 125),
               ctr_value='',
               label_style='normal',
               content_style='normal'):

    CtrlBase.__init__(self, parent=parent, label_style=label_style,
                      content_style=content_style)

    self.sizer = wx.GridBagSizer(5, 5)
    self.SetSizer(self.sizer)

    self.ctr = wx.richtext.RichTextCtrl(self,
                                        size=ctr_size,
                                        style=wx.VSCROLL,
                                        value=ctr_value)
    span_counter = 0
    if btn_import:
      self.btn_import = wx.Button(self,
                                  label=btn_import_label,
                                  size=btn_import_size)
      self.sizer.Add(self.btn_import, pos=(span_counter, 0))
      span_counter += 1
    if btn_export:
      self.btn_export = wx.Button(self,
                                  label=btn_export_label,
                                  size=btn_export_size)
      self.sizer.Add(self.btn_export, pos=(span_counter, 0))
      span_counter += 1
    if btn_default:
      self.btn_default = wx.Button(self,
                                   label=btn_default_label,
                                   size=btn_default_size)
      self.sizer.Add(self.btn_default, pos=(span_counter, 0))
      span_counter += 1

    if span_counter > 0:
      self.sizer.Add(self.ctr, pos=(0, 1), span=(span_counter + 1, 1),
                     flag=wx.EXPAND)
      self.sizer.AddGrowableRow(span_counter)
    elif span_counter == 0:
      self.sizer = wx.BoxSizer(wx.VERTICAL)
      self.sizer.Add(self.ctr, 1, flag=wx.EXPAND)

    self.sizer.AddGrowableCol(1)

class GaugeBar(CtrlBase):
  def __init__(self, parent,
               label='',
               label_size=(80, -1),
               label_style='normal',
               content_style='normal',
               gauge_size=(250, 15),
               button=False,
               button_label='View Stats',
               button_size=wx.DefaultSize,
               choice_box=True,
               choice_label='',
               choice_label_size=(120, -1),
               choice_size=(100, -1),
               choice_style='normal',
               choices=[],
               gauge_max=100):
    CtrlBase.__init__(self, parent=parent, label_style=label_style,
                      content_style=content_style)

    self.sizer = wx.FlexGridSizer(1, 6, 0, 10)
    self.sizer.AddGrowableCol(3)
    self.bar = wx.Gauge(self, range=gauge_max, size=gauge_size)

    if choice_box:
      self.bins = ChoiceCtrl(self,
                             label=choice_label,
                             label_size=choice_label_size,
                             label_style=choice_style,
                             ctrl_size=choice_size,
                             choices=choices)

    self.txt_iso = wx.StaticText(self, label=label, size=label_size)
    self.txt_max = wx.StaticText(self, label=str(gauge_max))
    self.txt_min = wx.StaticText(self, label='0')
    self.sizer.Add(self.txt_iso)
    self.sizer.Add(self.txt_min)
    self.sizer.Add(self.bar)
    self.sizer.Add(self.txt_max)
    self.sizer.Add(self.bins)

    if button:
      self.btn = wx.Button(self, label=button_label, size=button_size)
      self.sizer.Add(self.btn, 1, wx.ALIGN_RIGHT | wx.ALIGN_CENTER)

    self.SetSizer(self.sizer)


tp_EVT_STATUS_CHANGE = wx.NewEventType()
EVT_STATUS_CHANGE = wx.PyEventBinder(tp_EVT_STATUS_CHANGE, 1)

class StatusChange(wx.PyCommandEvent):
  ''' Send event when status light is updated '''
  def __init__(self, etype, eid, status=None):
    wx.PyCommandEvent.__init__(self, etype, eid)
    self.status = status
  def GetValue(self):
    return self.status

class SentinelStatus(CtrlBase):
  def __init__(self, parent,
               label='',
               label_size=(120, -1),
               label_style='normal',
               content_style='normal'):

    self.label = label
    self.label_size = label_size

    CtrlBase.__init__(self, parent=parent, label_style=label_style,
                      content_style=content_style, size=(-1, 24))

    bmp = wx.Bitmap('{}/16x16/led_off.png'.format(icons))
    self.light = wx.StaticBitmap(self, -1, bmp)

    self.sizer = wx.FlexGridSizer(1, 2, 0, 10)
    self.sizer.Add(self.light)
    self.sizer.Add(wx.StaticText(self, label=self.label, size=self.label_size))

    self.SetSizer(self.sizer)

    self.Bind(EVT_STATUS_CHANGE, self.onChangeStatus)

  def change_status(self, status):
    evt = StatusChange(tp_EVT_STATUS_CHANGE, -1, status)
    wx.PostEvent(self, evt)

  def onChangeStatus(self, evt):
    status = evt.GetValue()

    if status == 'on':
      bmp = wx.Bitmap('{}/16x16/led_on.png'.format(icons))
    elif status == 'off':
      bmp = wx.Bitmap('{}/16x16/led_off.png'.format(icons))
    elif status == 'idle':
      bmp = wx.Bitmap('{}/16x16/led_idle.png'.format(icons))
    elif status == 'alert':
      bmp = wx.Bitmap('{}/16x16/led_alert.png'.format(icons))

    self.light.SetBitmap(bmp)


class IsoformInfoCtrl(CtrlBase):
  def __init__(self, parent,
               label_style='normal',
               content_style='normal'):
    CtrlBase.__init__(self, parent=parent, label_style=label_style,
                      content_style=content_style)

    self.uc_values = None

    self.sizer = wx.FlexGridSizer(1, 9, 0, 10)
    self.sizer.AddGrowableCol(7)
    self.txt_iso = wx.StaticText(self, label='Isoform')
    self.txt_pg = wx.StaticText(self, label='Point Group')
    self.txt_num = wx.StaticText(self, label='No. Images')
    self.txt_uc = wx.StaticText(self, label='Unit Cell')

    self.ctr_iso = wx.TextCtrl(self, size=(30, -1), style=wx.TE_READONLY)
    self.ctr_pg = wx.TextCtrl(self, size=(50, -1), style=wx.TE_READONLY)
    self.ctr_num = wx.TextCtrl(self, size=(50, -1), style=wx.TE_READONLY)
    self.ctr_uc = wx.TextCtrl(self, size=(200, -1), style=wx.TE_READONLY)

    self.btn_hist = wx.Button(self, label='Histogram')

    self.sizer.Add(self.txt_iso, flag=wx.ALIGN_CENTER_VERTICAL)
    self.sizer.Add(self.ctr_iso, flag=wx.ALIGN_CENTER_VERTICAL)
    self.sizer.Add(self.txt_pg, flag=wx.ALIGN_CENTER_VERTICAL)
    self.sizer.Add(self.ctr_pg, flag=wx.ALIGN_CENTER_VERTICAL)
    self.sizer.Add(self.txt_num, flag=wx.ALIGN_CENTER_VERTICAL)
    self.sizer.Add(self.ctr_num, flag=wx.ALIGN_CENTER_VERTICAL)
    self.sizer.Add(self.txt_uc, flag=wx.ALIGN_CENTER_VERTICAL)
    self.sizer.Add(self.ctr_uc, flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
    self.sizer.Add(self.btn_hist, flag=wx.ALIGN_CENTER_VERTICAL)

    self.Bind(wx.EVT_BUTTON, self.onClusterHistogram, self.btn_hist)

    self.SetSizer(self.sizer)

  def onClusterHistogram(self, e):

    if self.uc_values is not None:
      import xfel.ui.components.xfel_gui_plotter as pltr
      plotter = pltr.PopUpCharts()
      plotter.plot_uc_histogram(info_list=[self.uc_values], legend_list=[])
      plotter.plt.show()
