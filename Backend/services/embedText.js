const use = require('@tensorflow-models/universal-sentence-encoder');
const tf = require('@tensorflow/tfjs-node');

let modelUSE = null;

async function loadUSE() {
  if (!modelUSE) {
    modelUSE = await use.load();
  }
  return modelUSE;
}

async function embedText(text) {
  const model = await loadUSE();
  const embeddings = await model.embed([text]);
  const embArray = embeddings.arraySync()[0];
  return embArray;
}

module.exports = {
  embedText,
};
