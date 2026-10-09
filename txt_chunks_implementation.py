# from fastapi import fastAPI

# app = fastAPI()

def read_and_chunk_financial_report():
    with open('financial_report.txt', "r") as testfile:
        f = testfile.read()
        split_points = []
        split_nl = f.split('\n')
        for i in range(len(split_nl)):
            content = split_nl[i]
        
            if content.isupper():
            
                split_points.append(i)
        chunks = []
        
        for i in range(len(split_nl)):
            content = split_nl[i].strip()
            if i in split_points:
                next_split = split_points.index(i) + 1

                if len(split_points) == next_split:
                    chunks.append(split_nl[i:])
                else:
                    chunks.append(split_nl[i: split_points[next_split]])

        return chunks
                    



read_and_chunk_financial_report()