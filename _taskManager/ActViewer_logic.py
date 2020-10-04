from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt

from _taskManager.ActViewer_design import Ui_actViewer
from _taskManager.nodes_list_logic import node_list_logic
from _taskManager.file_dialog import file_dialog
from util import print_nodes_name
from analytic import partialRlt_and_diff, visualize_weights

from PIL import Image
import re
import sys
import os
import numpy as np
import subprocess
import tensorflow as tf
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"


# logging
import logging
import log
logger = log.setup_custom_logger(__name__)
logger.setLevel(logging.INFO)


class actViewer_logic(QWidget, Ui_actViewer):
    def __init__(self, *args, **kwargs):
        super().__init__()

        self.setupUi(self)
        self.ckptButton.clicked.connect(self.ckptFileDialog)
        self.inputButton.clicked.connect(self.inputFileDialog)
        self.load.clicked.connect(self.load_activations)
        self.saveButton.clicked.connect(self.save_selected_activations)
        self.cancelButton.clicked.connect(self.exit)
        self.ckptPathLine.returnPressed.connect(self.set_ckpt)
        self.inputPathLine.returnPressed.connect(self.set_input)
        self.actList.doubleClicked.connect(self.set_focused_layer)
        self.actSlider.valueChanged.connect(self.display)

        # variables
        self.ckpt = None
        self.input = None
        self.layer = None

    def ckptFileDialog(self):
        tmp = file_dialog(title='choose .meta file').openFileNameDialog()
        if tmp is not None:
            self.ckptPathLine.setText(tmp)
            self.set_ckpt()

    def inputFileDialog(self):
        tmp = file_dialog(title='choose .tif for input').openFileNameDialog()
        if tmp is not None:
            self.inputPathLine.setText(tmp)
            self.set_input()

    def set_ckpt(self):
        self.ckpt = self.ckptPathLine.text()
        # hit Enter or close file dialog load automatically the model

        # prepare
        _re = re.search('(.+)ckpt/step(\d+)\.meta', self.ckpt)
        self.step = _re.group(2)
        self.graph_def_dir = _re.group(1)
        self.paths = {
            'step': self.step,
            'working_dir': self.graph_def_dir,
            'ckpt_dir': self.graph_def_dir + 'ckpt/',
            'ckpt_path': self.graph_def_dir + 'ckpt/step{}'.format(self.step),
            'save_pb_dir': self.graph_def_dir + 'pb/',
            'save_pb_path': self.graph_def_dir + 'pb/step{}.pb'.format(self.step),
            'data_dir': self.input,
        }

        model = re.search('mdl_([A-Za-z]*\d*)', self.ckpt).group(1)

        self.hyperparams = {
            'model': model,
            'window_size': int(re.search('ps(\d+)', self.ckpt).group(1)),
            'batch_size': int(re.search('bs(\d+)', self.ckpt).group(1)),
            # 'stride': args.stride,
            'device_option': 'cpu',
            'mode': 'classification',  # todo:
            'batch_normalization': False,
            'feature_map': True if model in ['LRCS8', 'LRCS9', 'LRCS10', 'Unet3'] else False,
        }

        self.load_graph()
        # get node and set the listViewWidget
        self.get_nodes()

    def set_input(self):
        self.input = self.inputPathLine.text()
        self.paths['data_dir'] = self.input

    def get_nodes(self):
        if self.input is None:
            self.set_input()

        graph = tf.get_default_graph().as_graph_def()
        nodes = print_nodes_name(graph)
        options = []
        for node in nodes:
            tmp = re.search('(^[a-zA-Z]+\d*\/).*(leaky|relu|sigmoid|tanh|logits\/identity|up\d+\/Reshape\_4|concat)$',
                            node)
            if tmp is not None:
                tmp = tmp.string
                options.append(tmp)
        self.actList.addItems([n for n in options])

    def set_focused_layer(self, list_number=None):
        self.layer = self.actList.item(list_number.row()).text()
        self.display()

    def display(self, nth=0):
        logger.debug(self.layer)
        if not hasattr(self, 'activations'):
            self.load_graph()
            self.load_activations()

        self.actSlider.setMaximum(len(self.activations))

        act = self.activations[self.layer][0][:, :, nth]
        act = (act - np.min(act)) / (np.max(act) - np.min(act)) * 255
        act = np.asarray(Image.fromarray(act).convert('RGB'))
        act = act.copy()

        self.q = QImage(act,
                             act.shape[1],
                             act.shape[0],
                             act.shape[1] * 3, QImage.Format_RGB888)
        self.p = QPixmap(self.q)
        self.p.scaled(self.width(), self.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.Images.setScaledContents(True)
        self.Images.setPixmap(self.p)
        self.Images.update()
        self.Images.repaint()

    def load_graph(self):
        # restore from ckpt the nodes
        tf.reset_default_graph()
        _ = tf.train.import_meta_graph(
            self.ckpt,
            clear_devices=True,
        )

    def load_activations(self):
        self.activations = partialRlt_and_diff(paths=self.paths, hyperparams=self.hyperparams,
                                          conserve_nodes=[self.actList.item(i).text() for i in range(self.actList.count())],
                                          write_rlt=False)
        logger.debug(self.activations)

        # todo: display the weight the input and output too
        # self.kern_name, self.kernels = visualize_weights(params=self.paths, write_rlt=False)
        # logger.debug(self.kern_name)

    def save_selected_activations(self):
        # if not selected, warn

        # if selected, save
        partialRlt_and_diff(paths=self.paths, hyperparams=self.hyperparams,
                            conserve_nodes=[self.actList.item(i).text() for i in range(self.actList.count())],
                            write_rlt=True)
        visualize_weights(params=self.paths, write_rlt=True)

    def exit(self):
        self.close()


def test():
    app = QApplication(sys.argv)

    # set ui
    ui = actViewer_logic()
    ui.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    test()