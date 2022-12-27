from flask import Flask, render_template, request #render:used to render HTML pages, request:access the data submitted in the frontend.
from werkzeug.utils import secure_filename #secures filename before storing it in the system
import pandas as pd #data analysis and manipulation tool
import os.path #process the files from different areas in the system


app = Flask(__name__)#creating an app variable and setting it to an instance of the Flask class

app.config["UPLOAD_FOLDER"] = "static/" #the path where to store the files

@app.route('/')
def upload_file():
    return render_template('index.html') #render our index.html page every time we go to server


def booking_reports(file):
    #create Pandas dataframe from Payout summary csv. Convert date columns to datetime format.
    booking_rep = pd.read_csv(file,parse_dates=['Departure or issue date','Payout date']) 
    
    #Add column "Total charge" to calculate total commission( sum of the columns "Commission" and "Payment charge")
    booking_rep['Total charge'] = booking_rep[['Commission', 'Payment charge']].sum(axis=1)
    
    #Net column contains the amount to be transfered. This column has to match the Bank statement incoming payments for Booking.com
    # Rename column "Net" to "Summa" to match the Bank Statement "Summa" column.
    booking_rep.rename(columns={"Net":"Summa"},inplace=True) #rename 
    
    #The payments are made to the host 4 times a months on the "Payout date" -group dataframe by payout date, sum the rows.
    booking_rep=booking_rep.groupby(by=["Payout date"],as_index=False).sum()
    
    #Data cleaning. Drop unnecessary and empty columns
    if 'Reference number' in  booking_rep.columns:
        booking_rep=booking_rep.drop(columns='Reference number')
    if 'Unnamed: 10' in booking_rep.columns:
        booking_rep=booking_rep.drop(columns='Unnamed: 10')
    if 'Payout ID' in  booking_rep.columns:
        booking_rep=booking_rep.drop(columns='Payout ID')
    return booking_rep

def bank_filter(bank):
    bank_filtered=pd.read_csv(bank,encoding='cp1252',parse_dates=['KuupÃ¤ev']) 
    bank_filtered = bank_filtered[['Saaja/maksja nimi', 'Summa','KuupÃ¤ev']]
    bank_filtered =  bank_filtered[ bank_filtered['Saaja/maksja nimi'].str.contains("Booking.com B.V.") == True]
    return bank_filtered

#create an empty list to append processed booking statements
apartment_list=[]

@app.route('/display', methods = ['GET', 'POST']) # #methods to accept get/post requests
def save_file():
    if request.method == 'POST':  #once the file is submitted, get the file and store it i a variable
        apartment_one = request.files['apartment1']
        apartment_two = request.files['apartment2']
        apartment_three= request.files['apartment3']
        bank= request.files['bank']

        app_list=[apartment_one,apartment_two,apartment_three] #create the list of booking payout statements.
    #If the user submits the form without selecting a file in the file field, then the filename is going to be an empty string,
    #so it is important to always check the filename to determine if a file is available or not.
        for file in app_list:         
            if not file: # Make sure, that the app will still work with one or two submitted payout statements
                pass
            else:
               file_name=secure_filename(file.filename) #get the name of the file, secure it and store it in filename.
               file.save(app.config['UPLOAD_FOLDER'] + file_name) #save the file in the directory. 
               file = open(app.config['UPLOAD_FOLDER'] +file_name,"r")#open the uploaded file in read-only mode. 
               
               files=booking_reports(file) # use previously created function to process each uploaded booking statement
               files["File_name"]=str(file_name) #add column with the filename
               apartment_list.append(files) #create collection of all processed booking statement dataframes.


    reports_joined= pd.concat(apartment_list,axis=0,ignore_index=False)
    reports_joined["Summa"]=reports_joined["Summa"].round(decimals=2)
    
    bank_statment=bank_filter(bank)
    booking_bank_joined=reports_joined.merge(bank_statment ,how='outer', on='Summa')
    booking_bank_joined.rename(columns={'Summa':'Payment',
                                        'KuupÃ¤ev':'Payment date',
                                         'Amount':'Room Sales',
                                         'Total charge':'Total commission',
                                         'Payout date':'Reported payout date'},inplace=True)   
    cols=['File_name','Reported payout date','Room Sales','Total commission','Payment','Payment date']
    booking_bank_joined=booking_bank_joined[cols] #show only required columns of the dataframe
    
    #rendering pandas dataframe as html table and pass in the contents of the file so that it can be displayed on our browser:
    return render_template('content.html', content=[booking_bank_joined.to_html(classes='data',header="true")])
   

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug = True)
    
#python main2.py