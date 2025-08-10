const tf = require('@tensorflow/tfjs-node');
const { embedText } = require('./services/embedText');

const LABELS = ['happy', 'sad', 'anxious'];

// Your labeled training data:
const trainingData = [
  { text: 'I am very happy today!', label: 0 },
  { text: 'Feeling sad and down.', label: 1 },
  { text: 'I am anxious about exams.', label: 2 },
  // Add more training samples here
];

async function trainModel() {
  const xs = [];
  const ys = [];

  for (const example of trainingData) {
    const embedding = await embedText(example.text);
    xs.push(embedding);
    ys.push(example.label);
  }

  const xsTensor = tf.tensor2d(xs);
  const ysTensor = tf.oneHot(tf.tensor1d(ys, 'int32'), LABELS.length);

  const model = tf.sequential();
  model.add(tf.layers.dense({ inputShape: [xs[0].length], units: 32, activation: 'relu' }));
  model.add(tf.layers.dense({ units: LABELS.length, activation: 'softmax' }));

  model.compile({
    optimizer: tf.train.adam(0.01),
    loss: 'categoricalCrossentropy',
    metrics: ['accuracy'],
  });

  await model.fit(xsTensor, ysTensor, {
    epochs: 50,
    batchSize: 2,
    callbacks: {
      onEpochEnd: (epoch, logs) => {
        console.log(`Epoch ${epoch}: loss=${logs.loss.toFixed(4)} accuracy=${logs.acc}`);
      },
    },
  });

  await model.save('file://./models/model-mood-classifier');
  console.log('Model training complete and saved.');
}

trainModel();
