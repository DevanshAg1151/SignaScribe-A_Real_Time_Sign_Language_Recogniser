from flask import Flask, render_template, redirect, jsonify,Response
import os
import tensorflow as tf
from object_detection.utils import label_map_util
from object_detection.utils import visualization_utils as viz_utils
from object_detection.builders import model_builder
from object_detection.utils import config_util
WORKSPACE_PATH = 'D:/Assignments/Sem 5/NTCC/Real Time Sign Language Recogniser/RealTimeObjectDetection/Tensorflow/workspace'
CUSTOM_MODEL_NAME = 'my_ssd_mobnet'
MODEL_PATH = WORKSPACE_PATH+'/models'
CHECKPOINT_PATH = MODEL_PATH+'/my_ssd_mobnet/'
CONFIG_PATH = MODEL_PATH+'/'+CUSTOM_MODEL_NAME+'/pipeline.config'
# Load pipeline config and build a detection model
configs = config_util.get_configs_from_pipeline_file(CONFIG_PATH)
detection_model = model_builder.build(model_config=configs['model'], is_training=False)

# Restore checkpoint
ckpt = tf.compat.v2.train.Checkpoint(model=detection_model)
ckpt.restore(os.path.join(CHECKPOINT_PATH, 'ckpt-36')).expect_partial()

def detect_fn(image):
    image, shapes = detection_model.preprocess(image)
    prediction_dict = detection_model.predict(image, shapes)
    detections = detection_model.postprocess(prediction_dict, shapes)
    return detections

import cv2 
import numpy as np
ANNOTATION_PATH = WORKSPACE_PATH+'/annotations'
category_index = label_map_util.create_category_index_from_labelmap(ANNOTATION_PATH+'/label_map.pbtxt')

def generate_frames():
    # Setup capture
    cap = cv2.VideoCapture(0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    while True:
        ret, frame = cap.read()
        if not ret:
            break;
        else:
            image_np = np.array(frame)
            
            input_tensor = tf.convert_to_tensor(np.expand_dims(image_np, 0), dtype=tf.float32)
            detections = detect_fn(input_tensor)
            
            num_detections = int(detections.pop('num_detections'))
            detections = {key: value[0, :num_detections].numpy()
                        for key, value in detections.items()}
            detections['num_detections'] = num_detections

            # detection_classes should be ints.
            detections['detection_classes'] = detections['detection_classes'].astype(np.int64)

            label_id_offset = 1
            image_np_with_detections = image_np.copy()

            viz_utils.visualize_boxes_and_labels_on_image_array(
                        image_np_with_detections,
                        detections['detection_boxes'],
                        detections['detection_classes']+label_id_offset,
                        detections['detection_scores'],
                        category_index,
                        use_normalized_coordinates=True,
                        max_boxes_to_draw=3,
                        min_score_thresh=.5,
                        agnostic_mode=False)

            # cv2.imshow('object detection',  cv2.resize(image_np_with_detections, (800, 600)))
            ret1, buffer = cv2.imencode('.jpg', cv2.resize(image_np_with_detections, (800, 600)))
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n'+frame+b'\r\n')
            
    cap.release()

app = Flask(__name__)

@app.route('/', methods=['GET','POST'])
def index():
    return render_template('home.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
@app.route('/sign_classifier',methods=['GET','POST'])
def sign_classifier():
    return render_template('sign_input.html')
