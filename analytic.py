import tensorflow as tf
import numpy as np
import pandas as pd
import os
from util import get_all_trainable_variables
from tsne import tsne, tsne_on_weights, tsne_on_weights_bis
from visualize import convert_ckpt2pb, built_diff_block, join_diff_to_mainGraph, run_nodes_and_save_partial_res



def tsne_partialRes_weights(*args, **kwargs):
    # load ckpt
    new_ph = tf.placeholder(tf.float32, shape=[200, 72, 72, 1], name='new_ph')

    # define nodes to conserve
    conserve_nodes = [
                'model/encoder/conv1/relu',
                'model/encoder/conv1bis/relu',
                'model/encoder/conv2/relu',
                'model/encoder/conv2bis/relu',
                'model/encoder/conv3/relu',
                'model/encoder/conv3bis/relu',
                'model/encoder/conv4/relu',
                'model/encoder/conv4bis/relu',
                'model/encoder/conv4bisbis/relu',
                'model/dnn/dnn1/relu',
                'model/dnn/dnn2/relu',
                'model/dnn/dnn3/relu',
                'model/decoder/deconv5/relu',
                'model/decoder/deconv5bis/relu',
                'model/decoder/deconv6/relu',
                'model/decoder/deconv6bis/relu',
                'model/decoder/deconv7bis/relu',
                'model/decoder/deconv7bis/relu',
                'model/decoder/deconv8/relu',
                'model/decoder/deconv8bis/relu',
                'model/decoder/deconv8bisbis/relu',
            ]

    # convert ckpt to pb
    convert_ckpt2pb(input=new_ph, conserve_nodes=conserve_nodes)

    # beforhand build diff block
    diff_block_gdef = built_diff_block()

    # graft diff block to main graph
    g_combined, ops_dict = join_diff_to_mainGraph(diff_block_gdef, conserve_nodes)

    # run nodes and save results
    run_nodes_and_save_partial_res(g_combined, ops_dict, conserve_nodes)

    # run tsne on wieghts
    # get weights from checkpoint
    wns, _, ws, _, _, _, _, _ = get_all_trainable_variables('./dummy/ckpt/step5/ckpt')

    # arange label and kernel
    new_wn = []
    new_ws = []
    grps = []
    for wn, w in zip(wns, ws):  # w.shape = [c_w, c_h, c_in, nb_conv]
        for i in range(w.shape[3]):
            new_wn.append(wn + '_{}'.format(i))  # e.g. conv4bis_96
            grps.append(wn.split('/')[0])

            #note: associativity: a x b + a x c = a x (b + c)
            # "...a kernel is the sum of all the dimensions in the previous layer..."
            # https://stackoverflow.com/questions/42712219/dimensions-in-convolutional-neural-network
            new_ws.append(np.sum(w[:, :, :, i], axis=2))  # e.g. (3, 3, 12, 24) [w, h, in, nb_conv] --> (3, 3, 24)

    # inject into t-SNE
    res = tsne(np.array(new_ws).transpose((1, 2, 0)).reshape(len(new_ws), -1))  # e.g. (3, 3, 1000) --> (9, 1000)

    # imshow
    # tsne_on_weights(res, new_wn)
    tsne_on_weights_bis(res, new_wn, grps)


def weights_hists_2csv():
    pass


#note
# construct dataframe
# header sheet_name conv1: [step0, step20, ...]
# header sheet_name conv1bis: [step0, step20, ...]
for step in os.listdir('./dummy/ckpt/'):
    # get weights-bias names and values
    wn, bn, ws, bs, dnn_wn, dnn_bn, dnn_ws, dnn_bs = get_all_trainable_variables('./dummy/ckpt/' + step + '/ckpt')

    # construct a dict of key: layer_name, value: flattened kernels
    dfs = {sheet_name.split(':')[0].replace('/', '_'): pd.DataFrame({step: params.flatten()})
           for sheet_name, params in zip(wn + bn + dnn_wn + dnn_bn, ws + bs + dnn_ws + dnn_bs)}

    # write into excel
    with pd.ExcelWriter('./result/params.xlsx', engine='xlsxwriter') as writer:
        for sheet_name in dfs.keys():
            dfs[sheet_name].to_excel(writer, sheet_name=sheet_name, index=False)


