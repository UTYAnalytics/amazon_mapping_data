from google.cloud import vision
import io
import requests  # Add this import for fetching content from URLs

def detect_features(url):
    """Detects features in the image at the specified URL."""
    client = vision.ImageAnnotatorClient()

    # Fetch content from the URL
    response = requests.get(url)
    content = response.content

    # Create an in-memory binary stream
    image_stream = io.BytesIO(content)

    image = vision.Image(content=image_stream.read())
    response = client.label_detection(image=image)
    labels = response.label_annotations

    return labels

def compare_images(image1_features, image2_features):
    """Compares two sets of image features to determine similarity."""
    # Example comparison logic: count how many labels match
    image1_labels = {label.description for label in image1_features}
    image2_labels = {label.description for label in image2_features}

    # Calculate similarity (this is a simplistic approach; you might need something more sophisticated)
    intersection = image1_labels.intersection(image2_labels)
    similarity_score = len(intersection) / min(len(image1_labels), len(image2_labels))
    return similarity_score

# Assuming you've downloaded the images or have them accessible via a path
# For URLs, you'll need to adjust the code to fetch the image and then pass the binary to Vision API

image1_features = detect_features('https://i5.walmartimages.com/seo/Hanes-White-A-Shirt-372-White-3XL-Pack-of-2_e2a5e203-059a-48c1-a8c8-889988ba63e4.ac478e76c2be4c4b69ff92c9ca705054.jpeg')
image2_features = detect_features('https://m.media-amazon.com/images/I/611VspQOSbL._AC_SL1000_.jpg')

similarity = compare_images(image1_features, image2_features)
print(f"Similarity score: {similarity}")


# import cv2
# import numpy as np
# import requests

# def fetch_image(url):
#     resp = requests.get(url)
#     image = np.asarray(bytearray(resp.content), dtype="uint8")
#     image = cv2.imdecode(image, cv2.IMREAD_COLOR)
#     return image

# def compare_images_orb(image1, image2):
#     # Initialize ORB detector
#     orb = cv2.ORB_create()
    
#     # Detect keypoints and descriptors
#     kp1, des1 = orb.detectAndCompute(image1, None)
#     kp2, des2 = orb.detectAndCompute(image2, None)
    
#     # Check if descriptors are found
#     if des1 is None or des2 is None:
#         return 0  # No descriptors, no similarity
    
#     # Create BFMatcher object
#     bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    
#     # Match descriptors
#     matches = bf.match(des1, des2)
    
#     # Sort them in the order of their distance
#     matches = sorted(matches, key=lambda x: x.distance)
    
#     # Only consider matches with a distance that indicates a good match.
#     # Distance below a certain threshold (e.g., 50) indicates a better match.
#     good_matches = [m for m in matches if m.distance < 50]
    
#     # Calculate similarity score: number of good matches divided by total number of matches
#     # This is a simple approach; you might want to consider more factors.
#     similarity_score = len(good_matches) / max(len(des1), len(des2))
    
#     return kp1, kp2, matches[:30], similarity_score  # Return the similarity score as well


# # URLs of the images to compare
# image_url1 = 'https://i5.walmartimages.com/seo/Hanes-White-A-Shirt-372-White-3XL-Pack-of-2_e2a5e203-059a-48c1-a8c8-889988ba63e4.ac478e76c2be4c4b69ff92c9ca705054.jpeg'
# image_url2 = 'https://m.media-amazon.com/images/I/611VspQOSbL._AC_SL1000_.jpg'

# # Fetch images
# image1 = fetch_image(image_url1)
# image2 = fetch_image(image_url2)

# # Compare images and get keypoints, matches, and the similarity score
# kp1, kp2, matches, similarity_score = compare_images_orb(image1, image2)

# print(f"Similarity score: {similarity_score:.2f}")

# # Visualization of the matches (optional)
# img_matches = cv2.drawMatches(image1, kp1, image2, kp2, matches, None, flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
# cv2.imshow("Matches", img_matches)
# cv2.waitKey(0)
# cv2.destroyAllWindows()