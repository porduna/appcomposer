window.ude = window.ude || {};
window.ude.commons = window.ude.commons || {};

ude.commons.NotificationClient = (function() {
    NotificationClient = function(clientId) {
        this.listeners = [];
        this._initServerConnection(clientId);
    };

    NotificationClient.prototype = {
        register: function(premise, callback) {
            this.listeners.push({
                premise: premise,
                callback: callback,
            });
        },

        processNotification: function(notification) {
            this.listeners.some(function(listener) {
                if (listener.premise(notification)) {
                    isGreedy = listener.callback(notification);
                    if (isGreedy) {
                        return true;
                    }
                }
                return false;
            });
        },

        _initServerConnection: function(clientID) {
            var socket = io.connect('http://go-lab.collide.info:80');
            socket.on(clientID, function(data) {
                this.processNotification(data);
            }.bind(this));
        },
    };

    return NotificationClient;
})();