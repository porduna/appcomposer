# This is an independent file to keep track of some TO-DOs



* db_helpers.save_bundles_to_db() is currently called everywhere (or it should be) in which the translate app data is
modified. This is meant to be an easy way to port the data to the DB without breaking everything, but is extremely
inefficient. Eventually the whole code should be cleaned up.