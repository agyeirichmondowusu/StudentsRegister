import os
import pickle
import numpy as np
import cv2
import face_recognition
from datetime import datetime
import shutil
import csv
import pandas as pd
import time
import fastapi
from fastapi import FastAPI, File, UploadFile, Request
import firebase_admin
from firebase_admin import credentials, storage
from firebase_admin import db
import uvicorn
import subprocess
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import gdown


serviceAccountPath = 'serviceAccountKey.json'

def downloadServiceAccountKey():
    try:
        gdown.download('https://drive.google.com/uc?id=1WVqDRC-gsO-AGr6DYeQ_0maeJYZkJh6E', serviceAccountPath, quiet=False)
    # https://drive.google.com/file/d/1WVqDRC-gsO-AGr6DYeQ_0maeJYZkJh6E/view?usp=sharing
        print(f'File Downloaded successfully')

    except Exception as e:
        print(f'An error occurered')

now = datetime.now()

global member_id

app = FastAPI()

image = None

# cap = cv2.VideoCapture(0)
# cap.set(3, 640)
# cap.set(4, 480)

attendanceFolderPath = "Attendance/"

# csv_root_dir_on_firebase = "Attendance_file"
csv_root_dir_on_firebase = "Attendance_file/"

csv_path_on_firebase = 'sunday_school.csv'
firebase_csv_attendance_file_path = f"{csv_root_dir_on_firebase}/{csv_path_on_firebase}"
sunday_school_csv = 'sunday_school.csv'


date_to_submit_attendance = datetime.now().strftime("%d-%B-%Y")#Date of attendance
time_to_submit_attendance = now.strftime("%I:%M %p")# time of attendance
body = f"On {date_to_submit_attendance}, {time_to_submit_attendance}, the update of the members present are indicated in the attached file."


folderPath = 'Images'
if not os.path.exists(folderPath):
    os.makedirs(folderPath, exist_ok=True)

pathList = os.listdir(folderPath)
print(pathList)
imgList = []
studentIds = []
recorded_ids = []


def findEncodings(imagesList):
    encodeList = []
    for img in imagesList:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)#Convert image from BGRtoRGB in orde to apply encodings
        encode = face_recognition.face_encodings(img)[0]# enough brightness is needed for encoding. Taking pictures in the dark will yeild errors only
        encodeList.append(encode)
        print(len(encodeList))


    return encodeList

def callEncodeGenerator():

    for path in pathList:
        imgList.append(cv2.imread(os.path.join(folderPath, path)))
        studentIds.append(os.path.splitext(path)[0])

        fileName = f'{folderPath}/{path}'

    print("Encoding Started ...")
    encodeListKnown = findEncodings(imgList)#stores encodings of images in encodeListKnown variable
    encodeListKnownWithIds = [encodeListKnown, studentIds] #maps the encodings of the images with the ids of the images 
    print("Encoding Complete")

    file = open("EncodeFile.p", 'wb')
    pickle.dump(encodeListKnownWithIds, file)#stores the mapped variable list in the file EncodeFile.p
    file.close()
    print("File Saved")
        
    print(studentIds)


def send_email_with_attachment():
    global body
    # Create the MIME message
    msg = MIMEMultipart()
    msg['From'] = "agyeirichmondowusu@gmail.com"
    msg['To'] = "richowusumond@gmail.com"
    msg['Subject'] = f"Attendance for {date_to_submit_attendance} at {time_to_submit_attendance}"

    # Attach the body of the email
    msg.attach(MIMEText(body, 'plain'))

    # Attach the CSV file
    try:
        # Open the CSV file in binary mode
        with open(csv_path_on_firebase, "rb") as attachment:
            # Create a MIMEBase object for the file
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            # Encode the file as base64
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename={csv_path_on_firebase.split('/')[-1]}")  # Attachment name
            msg.attach(part)
        print("CSV file attached successfully.")
    except Exception as e:
        print(f"Error attaching file: {e}")
        return

    # Set up the SMTP server and send the email
    try:
        # Connect to the SMTP server
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()  # Use TLS for security
        server.login("agyeirichmondowusu@gmail.com", "csuccatuunheymud")  # Log in to the server

        # Send the email
        server.sendmail("agyeirichmondowusu@gmail.com", "richowusumond@gmail.com", msg.as_string())
        server.quit()  # Close the connection
        print(f"Email sent to {"richowusumond@gmail.com"}")
    except Exception as e:
        print(f"Error sending email: {e}")



def download_all_files_from_firebase(folder_name, destination_folder):
    # Initialize Firebase Storage bucket
    bucket = storage.bucket()
    
    # Ensure the destination folder exists
    os.makedirs(destination_folder, exist_ok=True)
    
    # List all blobs (files) in the bucket
    blobs = bucket.list_blobs(prefix=folder_name)
    
    for blob in blobs:
        if blob.name.endswith('/'):
            continue
        # Create the full file path for the destination
        file_path = os.path.join(destination_folder, os.path.relpath(blob.name, folder_name))
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Download the blob to the destination file path
        blob.download_to_filename(file_path)
        print(f"Downloaded {blob.name} to {file_path}")


def upload_image_to_firebase(local_path, firebase_path):
    # Initialize Firebase Storage bucket
    # bucket = storage.bucket()
    bucket = storage.bucket()

    # Create a blob (file object) in the specified folder of Firebase Storage
    blob = bucket.blob(firebase_path)

    # Upload the image to the specified destination in Firebase Storage
    blob.upload_from_filename(local_path)

    # Make the URL publicly accessible
    # blob.make_public()
    print(f"Image uploaded to {blob.public_url}")


def upload_csv_to_firebase():
    # Create a blob (file object) in the specified folder of Firebase Storage
    bucket = storage.bucket()

    blob = bucket.blob(csv_path_on_firebase)

    # Upload the image to the specified destination in Firebase Storage
    blob.upload_from_filename(csv_path_on_firebase)

    # Make the URL publicly accessible
    # blob.make_public()
    print(f"File uploaded to {blob.public_url}")

def download_csv_file_from_firebase():
    bucket = storage.bucket()

    blob = bucket.blob(csv_root_dir_on_firebase)

    if not os.path.exists(csv_root_dir_on_firebase):  # Check if the directory exists
        os.makedirs(csv_root_dir_on_firebase, exist_ok=True)  # Create the directory if it doesn't exist

    filename = os.path.join(csv_root_dir_on_firebase, os.path.basename(csv_path_on_firebase))

    blob.download_to_filename(filename)
    print(f'CSV file downloaded and overwritten at {csv_root_dir_on_firebase}')

def download_csv_From_google_drive():        
    if not os.path.exists(csv_path_on_firebase):
        try:
            print('downloading csv file from drive')
            gdown.download('https://drive.google.com/uc?id=1dVv9cvVvgnkURmM4tIK3AM0REkgLzhCs', csv_path_on_firebase, quiet=False)
        except Exception as e:
            print('Error downloading csv file')
    # os.path.join('.', os.path.basename(csv_path_on_firebase))

download_csv_From_google_drive()
    # df = pd.read_csv(csv_path_on_firebase)
df = pd.read_csv(csv_path_on_firebase)

monitor_checked_attendance = {}
all_images = []

# Mark Attendance demo

global student_ID, att_images
student_ID = ''
att_images = []
student_exist = False
student_marked = ''

@app.post("/upload_id")
async def mark_attendance(request: Request):
    global student_marked, serviceAccountPath
    result = await request.json()
    id_img = result.get("ID")
    if not os.path.exists(serviceAccountPath):
        downloadServiceAccountKey()
    else:
        print("Service AccountKey exists already")
    if not firebase_admin._apps:
        cred = credentials.Certificate(serviceAccountPath)
        firebase_admin.initialize_app(cred, {#realtime db
        'databaseURL': "https://studentsdata-b20b4-default-rtdb.firebaseio.com/",
        'storageBucket': "studentsdata-b20b4.appspot.com"
        })
        bucket = storage.bucket()
    
    # download_csv_file_from_firebase()
    # if now.weekday() == 6 and now.hour == 5 and now.minute == 30:#Start attendance
    download_all_files_from_firebase(attendanceFolderPath, attendanceFolderPath)
    attendance_images = os.listdir(attendanceFolderPath)# Path to attendance images
    for attendance_img in attendance_images:
        att_images.append(cv2.imread(os.path.join(attendanceFolderPath, attendance_img)))#Actual Attendance Images

    download_all_files_from_firebase(folderPath, folderPath)
    callEncodeGenerator()
    # subprocess.run(["python3", "encodegenerator.py"])#Download and encode all registered images
    downloadFiles = os.listdir(folderPath)# Path to original images

    for img_path in downloadFiles:# Files of registered images only 
        all_images.append(cv2.imread(os.path.join(folderPath, img_path)))#Actual original images
    ############################################################
    date_format = datetime.now().strftime("%d, %b, %y")#Date of attendance
    
    new_column_name = f'{date_format}'

    print("new column name: ", new_column_name)
    print("Loading Encode File ...")
    file = open('EncodeFile.p', 'rb')
    encodeListKnownWithIds = pickle.load(file)
    file.close()
    encodeListKnown, memberIds = encodeListKnownWithIds#wen load the encodings of each person with their ids and store in the two variables. One for the encodings, and the other for the id of the person so we can compare the encoding in the variable
    print(memberIds)
    print("Encode File Loaded")


    for id in memberIds:
        monitor_checked_attendance.update({id: False})#Assigning all members attendance not taken

    for frame in att_images:
        # ret, frame = cap.read()
        
        reducedFrame = cv2.resize(frame, (0, 0), None, 0.25, 0.25)#scaling the frame down for processing
        
        faceCurLocation = face_recognition.face_locations(reducedFrame)#pointing to the location of the image in the frame
        encodeCurFrame = face_recognition.face_encodings(reducedFrame, faceCurLocation)
        print("type of faceCurLocation: ",type(faceCurLocation))
        print(faceCurLocation)

        if faceCurLocation:
            for encodeFace, faceLoc in zip(encodeCurFrame, faceCurLocation):
                matches = face_recognition.compare_faces(encodeListKnown, encodeFace, tolerance=0.5)
                faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)
                print("matches: ", matches)
                print("faceDis: ", faceDis)
                print("type of face dis", type(faceDis))
                

                matchIndex = np.argmin(faceDis)#returns the index of the first occurrence of the minimum value in the array
                print("match index", matchIndex)
                print("member id: ", memberIds[matchIndex])

                recorded_ids.append(memberIds[matchIndex])
                if matches[matchIndex]:
                    student_id = int(memberIds[matchIndex])#somce all ids are integers, student id must be converted into an integer before using it. The database wasn't having values for ID when we first used it, and that was why it wasn't updating the csv file
                    if not monitor_checked_attendance[str(student_id)]:# if attendance is not taken

                        print("type of member id: ", type(memberIds[matchIndex]))

                        time_of_attendance = now.strftime("%H:%M:%S")
                        if int(student_id) in df['ID'].values:
                            print("type of df[id]: ", type(df['ID']))
                            df.loc[df['ID'] == int(student_id), new_column_name] = time_of_attendance

                        df.to_csv(csv_path_on_firebase, index=False)

                        member_id = memberIds[matchIndex]
                        monitor_checked_attendance[member_id] = True
                        # cv2.putText(frame, f"Welcome {member_id}", (50, 100), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 0), 2)
                        # cv2.putText(frame, f'Welcome {str(member_id)}', (50, 100), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 0), 2)#to display the welcome message
                        student_marked = member_id
                        upload_csv_to_firebase()
                        send_email_with_attachment()
                        return student_marked
                
                else:
                    print(f"Closer to threshold {studentIds[matchIndex]}")
                    student_id = int(memberIds[matchIndex])#somce all ids are integers, student id must be converted into an integer before using it. The database wasn't having values for ID when we first used it, and that was why it wasn't updating the csv file
                    if not monitor_checked_attendance[str(student_id)]:# if attendance is not taken

                        print("type of member id: ", type(memberIds[matchIndex]))

                        time_of_attendance = f'{now.strftime("%H:%M:%S")}-low conf'
                        if int(student_id) in df['ID'].values:
                            print("type of df[id]: ", type(df['ID']))
                            df.loc[df['ID'] == int(student_id), new_column_name] = time_of_attendance

                        df.to_csv(csv_path_on_firebase, index=False)

                        member_id = memberIds[matchIndex]
                        monitor_checked_attendance[member_id] = True
                        # cv2.putText(frame, f"Welcome {member_id}", (50, 100), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 0), 2)
                        # cv2.putText(frame, f'Welcome {str(member_id)}', (50, 100), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 0), 2)#to display the welcome message
                        student_marked = member_id
                        upload_csv_to_firebase()
                        send_email_with_attachment()
    return recorded_ids
    

                 

    # cv2.imshow("Feed", frame)

cv2.destroyAllWindows()
# cap.release()



#make request to get all the other images and add the current one to it before encoding

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=3000)

