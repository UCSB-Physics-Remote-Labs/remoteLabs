// When the client receives a message from the server that message should go to the messageHandler
var signalling_server_hostname = location.hostname;
var signalling_server_address = signalling_server_hostname + location.pathname + "ws2";
var protocol = location.protocol === "https:" ? "wss:" : "ws:";
var port = 8081;
var wsurl = protocol + '//' + signalling_server_address;
// var wsurl_temp = 'ws://franck2.inst.physics.ucsb.edu:6048';

var dataChannel = new WebSocket(wsurl);

dataChannel.addEventListener('open', function (event) {
    console.log('Connected to server through websocket.');
});

dataChannel.addEventListener('close', function (event) {
    console.log('Websocket connection terminated.');
});


//Zak's Additional Function
function messageHandler(event) {
    console.log("MESSAGE HANDLER")
    var data = event.data;
    console.log(data);
    // Data should be the response from the server
    // controllerResponseHandler(data)
}