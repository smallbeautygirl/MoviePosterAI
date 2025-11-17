from imdb import Cinemagoer

# create an instance of the Cinemagoer class
ia = Cinemagoer()

# get a movie
movie = ia.get_movie("111161")  # 肖申克的救贖
ia.update(movie, info=["main", "full credits", "plot", "vote details"])

print(movie.keys())  # 你會看到 cast 出現
print(movie.get("cast")[:5])  # 顯示前 5 位演員

for key, value in movie.items():
    print(f"{key}: {value}")
# # print the names of the directors of the movie
# print("Directors:")
# for director in movie["directors"]:
#     print(director["name"])

# # print the genres of the movie
# print("Genres:")
# for genre in movie["genres"]:
#     print(genre)

# # search for a person name
# people = ia.search_person("Mel Gibson")
# for person in people:
#     print(person.personID, person["name"])
