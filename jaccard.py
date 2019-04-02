import numpy as np
from sklearn.metrics import jaccard_similarity_score
import json

def sortedValues(item):
    return [item[key] for key in sorted(item.keys())]

with open('property.json') as f:
    properties = json.load(f)

property = sortedValues(properties[0])
propertyToCompare = sortedValues(properties[1])

similarity = jaccard_similarity_score(property, propertyToCompare)

print('Jaccard similarity index of two similar properties:')
print(similarity)
