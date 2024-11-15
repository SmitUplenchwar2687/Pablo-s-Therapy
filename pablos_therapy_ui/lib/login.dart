import 'package:flutter/material.dart';
import 'session.dart';

class Login extends StatefulWidget {
  const Login({super.key});

  @override
  LoginState createState() => LoginState();
}

class LoginState extends State<Login> {
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _ageController = TextEditingController();
  String? _selectedGender;
  final List<String> _genders = ['Male', 'Female', 'Other'];

  final formKey = GlobalKey<FormState>();

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FilledButton(
      style: const ButtonStyle(
        backgroundColor: WidgetStatePropertyAll<Color>(Color(0xFF1A1A1A)),
      ),
      child: const Text('Start my Therapy'),
      onPressed: () => showDialog<String>(
        context: context,
        builder: (BuildContext context) => Dialog(
          child: Padding(
            padding: const EdgeInsets.all(8.0),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              mainAxisAlignment: MainAxisAlignment.center,
              children: <Widget>[
                const SizedBox(height: 40),
                Text(
                  'Start my Therapy',
                  style: Theme.of(context).textTheme.headlineMedium,
                ),
                const SizedBox(height: 15),
                Form(
                  key: formKey,
                  child: Column(
                    children: [
                      SizedBox(
                        width: 250,
                        child: TextFormField(
                          controller: _nameController,
                          decoration: const InputDecoration(
                            labelText: 'Enter Your Name',
                          ),
                          validator: (value) {
                            value = value?.trim() ?? '';
                            if (value.isEmpty) {
                              return 'Name is required';
                            }
                            return null;
                          },
                        ),
                      ),
                      SizedBox(
                        width: 250,
                        child: TextFormField(
                          controller: _ageController,
                          decoration: const InputDecoration(
                            labelText: 'Enter Your Age',
                          ),
                          validator: (value) {
                            value = value?.trim() ?? '';
                            if (value.isEmpty) {
                              return 'Age is required';
                            }
                            if (int.tryParse(value) == null) {
                              return 'Age must be a number';
                            }
                            return null;
                          },
                        ),
                      ),
                      SizedBox(
                        width: 250,
                        child: DropdownButtonFormField<String>(
                          value: _selectedGender,
                          decoration: const InputDecoration(
                            labelText: 'Select Gender',
                          ),
                          onChanged: (String? newValue) {
                            setState(() {
                              _selectedGender = newValue;
                            });
                          },
                          validator: (value) {
                            if (value == null || value.isEmpty) {
                              return 'Gender is required';
                            }
                            return null;
                          },
                          items: _genders.map((String gender) {
                            return DropdownMenuItem<String>(
                              value: gender,
                              child: Text(gender),
                            );
                          }).toList(),
                        ),
                      )
                    ],
                  ),
                ),
                const SizedBox(height: 15),
                FilledButton(
                  style: const ButtonStyle(
                    backgroundColor: WidgetStatePropertyAll<Color>(Color(0xFF1A1A1A)),
                  ),
                  child: const Text('Start my Therapy'),
                  onPressed: () {
                    if (formKey.currentState?.validate() ?? false) {
                      String enteredName = _nameController.text.trim();

                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) => Session(name: enteredName),
                        ),
                      );
                    }
                  },
                ),
                const SizedBox(height: 40),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
