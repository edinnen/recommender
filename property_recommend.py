import numpy as np
import pandas as pd
import tensorflow as tf

from sklearn import preprocessing
from sklearn.metrics import precision_score

k = 10

epochs = 10
display_step = 10

learning_rate = 0.3

batch_size = 250

train_data = "./train-1m.csv"
test_data = "./test-1m.csv"

# Reading dataset

df = pd.read_csv(train_data, names=['user', 'property', 'rating', 'timestamp'], header=None)
df = df.drop('timestamp', axis=1)

num_properties = df.property.nunique()
num_users = df.user.nunique()

print("USERS: {} PROPERTIES: {}".format(num_users, num_properties))


# Normalize in [0, 1]

r = df['rating'].values.astype(float)
min_max_scaler = preprocessing.MinMaxScaler()
x_scaled = min_max_scaler.fit_transform(r.reshape(-1,1))
df_normalized = pd.DataFrame(x_scaled)
df['rating'] = df_normalized


# Convert DataFrame in user-property matrix

matrix = df.pivot(index='user', columns='property', values='rating')
matrix.fillna(0, inplace=True)


# Users and properties ordered as they are in matrix

users = matrix.index.tolist()
properties = matrix.columns.tolist()

matrix = matrix.values

print("Matrix shape: {}".format(matrix.shape))

# num_users = matrix.shape[0]
# num_properties = matrix.shape[1]
# print("USERS: {} properties: {}".format(num_users, num_properties))


# Network Parameters

num_input = num_properties   # num of properties
num_hidden_1 = 10       # 1st layer num features
num_hidden_2 = 5        # 2nd layer num features (the latent dim)

X = tf.placeholder(tf.float64, [None, num_input])

weights = {
    'encoder_h1': tf.Variable(tf.random_normal([num_input, num_hidden_1], dtype=tf.float64)),
    'encoder_h2': tf.Variable(tf.random_normal([num_hidden_1, num_hidden_2], dtype=tf.float64)),
    'decoder_h1': tf.Variable(tf.random_normal([num_hidden_2, num_hidden_1], dtype=tf.float64)),
    'decoder_h2': tf.Variable(tf.random_normal([num_hidden_1, num_input], dtype=tf.float64)),
}

biases = {
    'encoder_b1': tf.Variable(tf.random_normal([num_hidden_1], dtype=tf.float64)),
    'encoder_b2': tf.Variable(tf.random_normal([num_hidden_2], dtype=tf.float64)),
    'decoder_b1': tf.Variable(tf.random_normal([num_hidden_1], dtype=tf.float64)),
    'decoder_b2': tf.Variable(tf.random_normal([num_input], dtype=tf.float64)),
}


# Building the encoder

def encoder(x):
    # Encoder Hidden layer with sigmoid activation #1
    layer_1 = tf.nn.sigmoid(tf.add(tf.matmul(x, weights['encoder_h1']), biases['encoder_b1']))
    # Encoder Hidden layer with sigmoid activation #2
    layer_2 = tf.nn.sigmoid(tf.add(tf.matmul(layer_1, weights['encoder_h2']), biases['encoder_b2']))
    return layer_2


# Building the decoder

def decoder(x):
    # Decoder Hidden layer with sigmoid activation #1
    layer_1 = tf.nn.sigmoid(tf.add(tf.matmul(x, weights['decoder_h1']), biases['decoder_b1']))
    # Decoder Hidden layer with sigmoid activation #2
    layer_2 = tf.nn.sigmoid(tf.add(tf.matmul(layer_1, weights['decoder_h2']), biases['decoder_b2']))
    return layer_2


# Construct model

encoder_op = encoder(X)
decoder_op = decoder(encoder_op)


# Prediction

y_pred = decoder_op


# Targets are the input data.

y_true = X


# Define loss and optimizer, minimize the squared error

loss = tf.losses.mean_squared_error(y_true, y_pred)
optimizer = tf.train.RMSPropOptimizer(learning_rate).minimize(loss)

predictions = pd.DataFrame()

# Define evaluation metrics

eval_x = tf.placeholder(tf.int32, )
eval_y = tf.placeholder(tf.int32, )
pre, pre_op = tf.metrics.precision(labels=eval_x, predictions=eval_y)


# Initialize the variables (i.e. assign their default value)

init = tf.global_variables_initializer()
local_init = tf.local_variables_initializer()

with tf.Session() as session:
    session.run(init)
    session.run(local_init)

    num_batches = int(matrix.shape[0] / batch_size)
    matrix = np.array_split(matrix, num_batches)

    for i in range(epochs):

        avg_cost = 0

        for batch in matrix:
            _, l = session.run([optimizer, loss], feed_dict={X: batch})
            avg_cost += l

        avg_cost /= num_batches

        print("Epoch: {} Loss: {}".format(i + 1, avg_cost))

        # if i % display_step == 0 or i == 1:
        #     print('Step %i: Minibatch Loss: %f' % (i, l))

    print("Predictions...")

    matrix = np.concatenate(matrix, axis=0)

    preds = session.run(decoder_op, feed_dict={X: matrix})

    # print(matrix)
    # print(preds)

    predictions = predictions.append(pd.DataFrame(preds))

    predictions = predictions.stack().reset_index(name='rating')
    predictions.columns = ['user', 'property', 'rating']
    predictions['user'] = predictions['user'].map(lambda value: users[value])
    predictions['property'] = predictions['property'].map(lambda value: properties[value])

    # print(predictions)

    print("Filtering out properties in training set")

    keys = ['user', 'property']
    i1 = predictions.set_index(keys).index
    i2 = df.set_index(keys).index

    recs = predictions[~i1.isin(i2)]
    recs = recs.sort_values(['user', 'rating'], ascending=[True, False])
    recs = recs.groupby('user').head(k)
    recs.to_csv('recs.tsv', index=False, header=False)
    print('done')
