EcoTaxa registration and password recovery mail templates  
==
Templates used by the user registration and validation system.

## JSON templates

 - **verify.json** : message for email verification (create,update) when email validation is "on".
 - **modify.json** : message asking the user to modify one or more values in his profile when account validation is "on".  
 - **activate.json** : message sent to the user manager when account validation is "on" at registration or profile update. 
 - **status.json** : message sent to the user when the status of the account has changed.
 - **password_reset.json** : message for password reset request. 

## keys

 - **language** (en_EN)
	 - **action** : create , update , modify
		 - **url** :  the call to action url 
		 - **subject** : the mail subject
		 - **email** : the assistance email
		 - **assistance** : assistance message with email
		  - **link** : format the call to action url with other values ( token for example)
		  -  **data** :  insert pre-formatted registration data (key, value variables)
		  - **body** : the mail body 

## Variables
*(other than keys)*
 - **id** :   the user id
 - **token** : token ( with a validity period)
 - **registration data : key , value** : registration data
 - **reason** : additional text 
 - **ticket** : for ticketing system (OTRS etc...)
